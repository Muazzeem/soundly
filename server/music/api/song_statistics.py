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
        # Fetch relevant exchanges
        user_exchanges = SongExchange.objects.filter(
            Q(receiver=user) |
            Q(sender=user, status='completed')
        ).select_related('sender', 'receiver')

        # Count stats
        songs_shared = SongExchange.objects.filter(sender=user).count()
        songs_received = SongExchange.objects.filter(receiver=user).count()
        received_or_completed = user_exchanges

        # Track data
        exchange_partners = set()
        countries, cities = set(), set()
        country_stats, city_stats, city_country_combinations = {}, {}, {}

        for exchange in received_or_completed:
            partner = exchange.sender if exchange.receiver == user else exchange.receiver
            if not partner:
                continue

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

        response_data = {
            'songs_shared': songs_shared,
            'songs_received': songs_received,
            'songs_received_or_completed': received_or_completed.count(),
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
                'countries': [
                    {'country': c, **stats} for c, stats in top_countries
                ],
                'cities': [
                    {'city': c, **stats} for c, stats in top_cities
                ]
            }
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'An error occurred while fetching statistics: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_summary_statistics(request):
    user = request.user

    try:
        # Songs Shared
        songs_shared = SongExchange.objects.filter(sender=user).count()

        # Unique Connections (users exchanged with as sender or receiver)
        exchange_partners = SongExchange.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).exclude(
            Q(sender=user, receiver=None) | Q(receiver=user, sender=None)
        ).values_list(
            'sender', 'receiver'
        )

        partner_ids = set()
        for sender_id, receiver_id in exchange_partners:
            if sender_id and sender_id != user.id:
                partner_ids.add(sender_id)
            if receiver_id and receiver_id != user.id:
                partner_ids.add(receiver_id)

        countries = User.objects.filter(id__in=partner_ids).exclude(country__isnull=True).values_list('country', flat=True).distinct()

        # Days active (from first song exchange to today)
        first_exchange = SongExchange.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).order_by('created_at').first()

        if first_exchange:
            days_active = (now().date() - first_exchange.created_at.date()).days + 1
        else:
            days_active = 0

        response_data = {
            'songs_shared': songs_shared,
            'connections': len(partner_ids),
            'countries': len(countries),
            'days_active': days_active
        }

        return Response(response_data, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'An error occurred while fetching user summary: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
