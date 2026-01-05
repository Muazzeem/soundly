from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from music.models import SongExchange
from users.api.serializers import UserSerializer

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
                'songs_received': songs_received,
                'countries_list': list(countries) if countries else [],
                'cities_list': list(cities) if cities else [],
            },
            'geographical_breakdown': {
                'by_country': country_breakdown,
                'by_city': city_breakdown,
                'by_city_country': city_country_breakdown
            },
            'top_locations': {
                'countries': [
                    {'country': c, **stats} for c, stats in top_countries
                ] if top_countries else [],
                'cities': [
                    {'city': c, **stats} for c, stats in top_cities
                ] if top_cities else []
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def connected_users_list(request):
    """Return list of users that the current user has exchanged songs with"""
    user = request.user

    try:
        # Get all exchanges where user is sender or receiver
        user_exchanges = SongExchange.objects.filter(
            Q(sender=user) | Q(receiver=user)
        ).exclude(
            Q(sender=user, receiver=None) | Q(receiver=user, sender=None)
        ).select_related('sender', 'receiver')

        # Collect unique partner IDs and count exchanges
        partner_ids = set()
        partner_exchange_counts = {}
        
        for exchange in user_exchanges:
            if exchange.sender == user and exchange.receiver:
                partner_id = exchange.receiver.id
            elif exchange.receiver == user and exchange.sender:
                partner_id = exchange.sender.id
            else:
                continue
            
            if partner_id != user.id:
                partner_ids.add(partner_id)
                partner_exchange_counts[partner_id] = partner_exchange_counts.get(partner_id, 0) + 1

        # Fetch partner users
        partners = User.objects.filter(id__in=partner_ids)

        # Serialize users
        serializer = UserSerializer(partners, many=True, context={'request': request})
        users_data = serializer.data

        # Add exchange count to each user
        for user_data in users_data:
            user_id = user_data.get('pk') or user_data.get('id')
            if user_id:
                user_data['songs_exchanged'] = partner_exchange_counts.get(user_id, 0)

        # Sort by songs exchanged (descending)
        users_data.sort(key=lambda x: x.get('songs_exchanged', 0), reverse=True)

        return Response({
            'count': len(users_data),
            'results': users_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'An error occurred while fetching connected users: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_statistics_by_uid(request, user_uid):
    """Get statistics for a specific user by their UID"""
    try:
        target_user = User.objects.get(uid=user_uid)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    try:
        # Fetch relevant exchanges for the target user
        user_exchanges = SongExchange.objects.filter(
            Q(receiver=target_user) |
            Q(sender=target_user, status='completed')
        ).select_related('sender', 'receiver')

        # Count stats
        songs_shared = SongExchange.objects.filter(sender=target_user).count()
        songs_received = SongExchange.objects.filter(receiver=target_user).count()
        received_or_completed = user_exchanges

        # Track data
        exchange_partners = set()
        countries = set()
        cities = set()
        country_stats = {}
        city_stats = {}

        for exchange in received_or_completed:
            partner = exchange.sender if exchange.receiver == target_user else exchange.receiver
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
        top_countries = sorted(country_breakdown.items(), key=lambda x: x[1]['users_count'], reverse=True)[:10]
        top_cities = sorted(city_breakdown.items(), key=lambda x: x[1]['users_count'], reverse=True)[:10]

        response_data = {
            'songs_shared': songs_shared,
            'songs_received': songs_received,
            'users_exchanged_with': len(exchange_partners),
            'countries_involved': len(countries),
            'top_locations': {
                'countries': [
                    {'country': c, **stats} for c, stats in top_countries
                ] if top_countries else [],
                'cities': [
                    {'city': c, **stats} for c, stats in top_cities
                ] if top_cities else []
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
def connected_users_list_by_uid(request, user_uid):
    """Return list of users that a specific user has exchanged songs with"""
    try:
        target_user = User.objects.get(uid=user_uid)
    except User.DoesNotExist:
        return Response(
            {'error': 'User not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    try:
        # Get all exchanges where target user is sender or receiver
        user_exchanges = SongExchange.objects.filter(
            Q(sender=target_user) | Q(receiver=target_user)
        ).exclude(
            Q(sender=target_user, receiver=None) | Q(receiver=target_user, sender=None)
        ).select_related('sender', 'receiver')

        # Collect unique partner IDs and count exchanges
        partner_ids = set()
        partner_exchange_counts = {}
        
        for exchange in user_exchanges:
            if exchange.sender == target_user and exchange.receiver:
                partner_id = exchange.receiver.id
            elif exchange.receiver == target_user and exchange.sender:
                partner_id = exchange.sender.id
            else:
                continue
            
            if partner_id != target_user.id:
                partner_ids.add(partner_id)
                partner_exchange_counts[partner_id] = partner_exchange_counts.get(partner_id, 0) + 1

        # Fetch partner users
        partners = User.objects.filter(id__in=partner_ids)

        # Serialize users
        serializer = UserSerializer(partners, many=True, context={'request': request})
        users_data = serializer.data

        # Add exchange count to each user
        for user_data in users_data:
            user_id = user_data.get('pk') or user_data.get('id')
            if user_id:
                user_data['songs_exchanged'] = partner_exchange_counts.get(user_id, 0)

        # Sort by songs exchanged (descending)
        users_data.sort(key=lambda x: x.get('songs_exchanged', 0), reverse=True)

        return Response({
            'count': len(users_data),
            'results': users_data
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response(
            {'error': f'An error occurred while fetching connected users: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
