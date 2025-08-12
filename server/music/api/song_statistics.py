from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from music.models import SongExchange

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def song_exchange_statistics(request):
    user = request.user

    try:
        # Get all exchanges involving the user
        exchanges = SongExchange.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).select_related('sender', 'receiver')

        # Filter only matched or completed to avoid pending noise
        exchanges = exchanges.filter(status__in=['matched', 'completed'])

        # Songs shared/received
        songs_shared = SongExchange.objects.filter(sender=user, status__in=['matched', 'completed']).count()
        songs_received = SongExchange.objects.filter(receiver=user, status__in=['matched', 'completed']).count()

        # Track partners & location stats without double counting
        exchange_partners = set()
        countries, cities = set(), set()
        country_stats, city_stats, city_country_combinations = {}, {}, {}

        # Deduplicate by unique pair of users to avoid double counting
        seen_pairs = set()

        for exchange in exchanges:
            partner = exchange.receiver if exchange.sender == user else exchange.sender
            if not partner:
                continue

            pair_key = tuple(sorted([user.id, partner.id]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            exchange_partners.add(partner.id)

            if partner.country:
                countries.add(partner.country)
                stats = country_stats.setdefault(partner.country, {'users': set(), 'exchanges': 0})
                stats['users'].add(partner.id)
                stats['exchanges'] += 1

            if partner.city:
                cities.add(partner.city)
                stats = city_stats.setdefault(partner.city, {
                    'users': set(),
                    'exchanges': 0,
                    'country': partner.country or 'Unknown'
                })
                stats['users'].add(partner.id)
                stats['exchanges'] += 1

            if partner.city and partner.country:
                key = f"{partner.city}, {partner.country}"
                stats = city_country_combinations.setdefault(key, {'users': set(), 'exchanges': 0})
                stats['users'].add(partner.id)
                stats['exchanges'] += 1

        def summarize_stats(stats_dict):
            return {
                key: {
                    'users_count': len(value['users']),
                    'songs_exchanged': value['exchanges'],
                    **({'country': value['country']} if 'country' in value else {})
                }
                for key, value in stats_dict.items()
            }

        country_breakdown = summarize_stats(country_stats)
        city_breakdown = summarize_stats(city_stats)
        city_country_breakdown = summarize_stats(city_country_combinations)

        top_countries = sorted(country_breakdown.items(), key=lambda x: x[1]['users_count'], reverse=True)[:10]
        top_cities = sorted(city_breakdown.items(), key=lambda x: x[1]['users_count'], reverse=True)[:10]

        return Response({
            'songs_shared': songs_shared,
            'songs_received': songs_received,
            'total_unique_exchanges': len(seen_pairs),
            'users_exchanged_with': len(exchange_partners),
            'countries_involved': len(countries),
            'detailed_stats': {
                'countries_list': list(countries),
                'cities_list': list(cities),
            },
            'geographical_breakdown': {
                'by_country': country_breakdown,
                'by_city': city_breakdown,
                'by_city_country': city_country_breakdown
            },
            'top_locations': {
                'countries': [{'country': c, **stats} for c, stats in top_countries],
                'cities': [{'city': c, **stats} for c, stats in top_cities]
            }
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_summary_statistics(request):
    user = request.user

    try:
        # Get unique exchange partners (avoid double counting reverse matches)
        partner_ids = set()
        exchanges = SongExchange.objects.filter(Q(sender=user) | Q(receiver=user)).filter(status__in=['matched', 'completed'])
        seen_pairs = set()

        for exchange in exchanges:
            partner = exchange.receiver if exchange.sender == user else exchange.sender
            if not partner:
                continue
            pair_key = tuple(sorted([user.id, partner.id]))
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)
            partner_ids.add(partner.id)

        # Songs shared (unique sent songs)
        songs_shared = SongExchange.objects.filter(sender=user, status__in=['matched', 'completed']).values('sent_song').distinct().count()

        # Countries connected with
        countries = User.objects.filter(id__in=partner_ids).exclude(country__isnull=True).values_list('country', flat=True).distinct()

        # Days active
        first_exchange = exchanges.order_by('created_at').first()
        days_active = (now().date() - first_exchange.created_at.date()).days + 1 if first_exchange else 0

        return Response({
            'songs_shared': songs_shared,
            'connections': len(partner_ids),
            'countries': len(countries),
            'days_active': days_active
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
