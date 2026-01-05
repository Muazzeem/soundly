from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.auth import get_user_model
from core.models import Activity, ActivityReaction, ActivityComment
from music.models import SongExchange
from core.decorators import handle_api_errors
from django.db.models import Count
from users.models import Friendship
import pycountry
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


def _get_aggregated_comment_count(activity):
    """
    Get the total comment count for an activity.
    For song exchanges, aggregate comments from both related activities.
    """
    if activity.activity_type == 'song_exchange' and activity.song_exchange:
        exchange = activity.song_exchange
        # Find the reciprocal exchange
        reciprocal_exchange = None
        if exchange.sender and exchange.receiver and exchange.sent_song and exchange.received_song:
            reciprocal_exchange = SongExchange.objects.filter(
                sender=exchange.receiver,
                receiver=exchange.sender,
                sent_song=exchange.received_song,
                received_song=exchange.sent_song,
                status='matched'
            ).first()
        
        # Get all activities for both exchanges
        activity_ids = [activity.id]
        if reciprocal_exchange:
            reciprocal_activities = Activity.objects.filter(
                song_exchange=reciprocal_exchange,
                activity_type='song_exchange'
            )
            activity_ids.extend([a.id for a in reciprocal_activities])
        
        # Count all comments from all related activities
        return ActivityComment.objects.filter(activity_id__in=activity_ids).count()
    else:
        # For non-exchange activities, just count comments for this activity
        return ActivityComment.objects.filter(activity=activity).count()


@api_view(["GET"])
@handle_api_errors
def country_list(request):
    # Input validation
    search = request.GET.get("search", "").strip().lower()
    
    if search and len(search) > 100:
        logger.warning(f"Country search query too long: {len(search)} characters")
        return Response(
            {"error": "Search query must be less than 100 characters"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        countries = list(pycountry.countries)

        if search:
            countries = [c for c in countries if search in c.name.lower()]

        def get_flag_emoji(alpha_2):
            return chr(ord(alpha_2[0].upper()) + 127397) + chr(ord(alpha_2[1].upper()) + 127397)

        result = [
            {
                "name": c.name,
                "alpha_2": c.alpha_2,
                "alpha_3": c.alpha_3,
                "flag_url": f"https://flagcdn.com/w40/{c.alpha_2.lower()}.png",
            }
            for c in countries
        ]
        return Response(result, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error in country_list: {str(e)}", exc_info=True)
        return Response(
            {"error": "Failed to fetch countries"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@handle_api_errors
def activity_feed(request):
    """
    Get activity feed from all users
    Query parameter: ?scope=all (default) - shows all activities
    Shows only song exchanges (no discoveries)
    """
    user = request.user
    scope = request.GET.get('scope', 'all').strip().lower()  # Default to 'all' - show all activities
    
    # Input validation
    if scope not in ['all', 'friends']:
        logger.warning(f"Invalid scope '{scope}' from user {user.email}")
        scope = 'all'  # Default to 'all' if invalid
    
    logger.info(f"Activity feed requested by {user.email} with scope={scope}")
    
    # For debugging: log exchange activities
    exchange_activities = Activity.objects.filter(activity_type='song_exchange').count()
    logger.debug(f"Total exchange activities in DB: {exchange_activities}")
    
    if scope == 'all':
        # Get only song exchange activities from all users
        # Since we now create only ONE activity per exchange (with sender as actor),
        # we need to show exchanges where the user is either sender or receiver
        # But exclude activities where the user is the actor (to avoid showing their own activities)
        activities = Activity.objects.filter(
            activity_type='song_exchange'
        ).exclude(
            actor=user
        ).select_related(
            'actor',
            'song',
            'song_exchange',
            'song_exchange__sent_song',
            'song_exchange__received_song',
            'song_exchange__sender',
            'song_exchange__receiver',
            'song__platform'
        ).order_by('-created_at')
        
        # Additional deduplication by song_exchange to ensure no duplicates
        # (safety measure in case old duplicate activities exist)
        seen_exchanges = set()
        unique_activities = []
        for activity in activities:
            if activity.song_exchange:
                exchange_id = activity.song_exchange.uid
                if exchange_id not in seen_exchanges:
                    seen_exchanges.add(exchange_id)
                    unique_activities.append(activity)
                    if len(unique_activities) >= 50:  # Limit to 50 most recent
                        break
        
        activities_list = unique_activities
        logger.info(f"Found {len(activities_list)} unique exchange activities from all users (deduplicated)")
    else:
        # Get all friends
        friendships = Friendship.objects.filter(
            Q(requester=user) | Q(addressee=user),
            status='accepted'
        ).select_related('requester', 'addressee')
        
        friend_ids = []
        for friendship in friendships:
            if friendship.requester == user:
                friend_ids.append(friendship.addressee.id)
            else:
                friend_ids.append(friendship.requester.id)
        
        if not friend_ids:
            return Response({
                'count': 0,
                'activities': [],
                'message': 'No friends yet. Add friends to see their activity!',
                'scope': 'friends'
            })
        
        # Get only song exchange activities from friends
        # Since we now create only ONE activity per exchange, we show activities where
        # the actor is a friend, but we also need to include exchanges where a friend is the receiver
        # However, since activities are created with sender as actor, we just filter by actor in friends
        activities = Activity.objects.filter(
            actor_id__in=friend_ids,
            activity_type='song_exchange'
        ).select_related(
            'actor',
            'song',
            'song_exchange',
            'song_exchange__sent_song',
            'song_exchange__received_song',
            'song_exchange__sender',
            'song_exchange__receiver',
            'song__platform'
        ).order_by('-created_at')
        
        # Additional deduplication by song_exchange (safety measure)
        seen_exchanges = set()
        unique_activities = []
        for activity in activities:
            if activity.song_exchange:
                exchange_id = activity.song_exchange.uid
                if exchange_id not in seen_exchanges:
                    seen_exchanges.add(exchange_id)
                    unique_activities.append(activity)
                    if len(unique_activities) >= 50:  # Limit to 50 most recent
                        break
        
        activities_list = unique_activities
        logger.info(f"Found {len(activities_list)} unique exchange activities from {len(friend_ids)} friends (deduplicated)")
    
    # Use the deduplicated activities list
    activities = activities_list
    
    # Serialize activities
    feed_data = []
    for activity in activities:
        profile_image_url = None
        if activity.actor.profile_image:
            try:
                profile_image_url = request.build_absolute_uri(activity.actor.profile_image.url)
            except:
                profile_image_url = None
        
        actor_data = {
            'uid': str(activity.actor.uid),
            'name': activity.actor.display_name,
            'email': activity.actor.email,
            'profile_image_url': profile_image_url,
        }
        
        # Get user's reaction if exists
        user_reaction = None
        try:
            user_reaction_obj = ActivityReaction.objects.filter(
                activity=activity,
                user=user
            ).first()
            if user_reaction_obj:
                user_reaction = user_reaction_obj.reaction_type
        except:
            pass
        
        # Get reactions summary
        reactions_summary = {}
        try:
            reactions = ActivityReaction.objects.filter(activity=activity).select_related('user')
            for reaction in reactions:
                reaction_type = reaction.reaction_type
                if reaction_type not in reactions_summary:
                    reactions_summary[reaction_type] = {
                        'count': 0,
                        'users': []
                    }
                reactions_summary[reaction_type]['count'] += 1
                if len(reactions_summary[reaction_type]['users']) < 3:
                    reactions_summary[reaction_type]['users'].append({
                        'uid': str(reaction.user.uid),
                        'name': reaction.user.display_name,
                    })
        except:
            pass
        
        # Get comments (limit to 5 most recent)
        # For song exchanges, aggregate comments from both related activities
        comments_data = []
        try:
            if activity.activity_type == 'song_exchange' and activity.song_exchange:
                exchange = activity.song_exchange
                # Find the reciprocal exchange
                reciprocal_exchange = None
                if exchange.sender and exchange.receiver and exchange.sent_song and exchange.received_song:
                    reciprocal_exchange = SongExchange.objects.filter(
                        sender=exchange.receiver,
                        receiver=exchange.sender,
                        sent_song=exchange.received_song,
                        received_song=exchange.sent_song,
                        status='matched'
                    ).first()
                
                # Get all activities for both exchanges
                activity_ids = [activity.id]
                if reciprocal_exchange:
                    reciprocal_activities = Activity.objects.filter(
                        song_exchange=reciprocal_exchange,
                        activity_type='song_exchange'
                    )
                    activity_ids.extend([a.id for a in reciprocal_activities])
                
                # Get comments from all related activities
                comments = ActivityComment.objects.filter(
                    activity_id__in=activity_ids
                ).select_related('user').order_by('created_at')[:5]
            else:
                # For non-exchange activities, just get comments for this activity
                comments = ActivityComment.objects.filter(
                    activity=activity
                ).select_related('user').order_by('created_at')[:5]
            
            for comment in comments:
                comment_actor_url = None
                if comment.user.profile_image:
                    try:
                        comment_actor_url = request.build_absolute_uri(comment.user.profile_image.url)
                    except:
                        pass
                
                comments_data.append({
                    'uid': str(comment.uid),
                    'user': {
                        'uid': str(comment.user.uid),
                        'name': comment.user.display_name,
                        'profile_image_url': comment_actor_url,
                    },
                    'text': comment.text,
                    'created_at': comment.created_at.isoformat(),
                })
        except:
            pass
        
        activity_data = {
            'uid': str(activity.uid),
            'activity_type': activity.activity_type,
            'actor': actor_data,
            'created_at': activity.created_at.isoformat(),
            'extra_data': activity.extra_data,
            'reactions': reactions_summary,
            'reactions_count': sum(r['count'] for r in reactions_summary.values()),
            'user_reaction': user_reaction,
            'comments': comments_data,
            'comments_count': _get_aggregated_comment_count(activity),
        }
        
        if activity.activity_type == 'song_exchange' and activity.song_exchange:
            exchange = activity.song_exchange
            # Build profile image URLs safely
            receiver_profile_url = None
            if exchange.receiver and exchange.receiver.profile_image:
                try:
                    receiver_profile_url = request.build_absolute_uri(exchange.receiver.profile_image.url)
                except:
                    pass
            
            sender_profile_url = None
            if exchange.sender and exchange.sender.profile_image:
                try:
                    sender_profile_url = request.build_absolute_uri(exchange.sender.profile_image.url)
                except:
                    pass
            
            activity_data['exchange'] = {
                'uid': str(exchange.uid),
                'match_type': exchange.match_type,
                'sent_song': {
                    'uid': str(exchange.sent_song.uid),
                    'title': exchange.sent_song.title,
                    'artist': exchange.sent_song.artist,
                    'url': exchange.sent_song.url,
                    'cover_image_url': exchange.sent_song.cover_image_url,
                    'genre': exchange.sent_song.genre,
                } if exchange.sent_song else None,
                'received_song': {
                    'uid': str(exchange.received_song.uid),
                    'title': exchange.received_song.title,
                    'artist': exchange.received_song.artist,
                    'url': exchange.received_song.url,
                    'cover_image_url': exchange.received_song.cover_image_url,
                    'genre': exchange.received_song.genre,
                } if exchange.received_song else None,
                'receiver': {
                    'uid': str(exchange.receiver.uid),
                    'name': exchange.receiver.display_name,
                    'profession': exchange.receiver.profession,
                    'city': exchange.receiver.city,
                    'country': exchange.receiver.country,
                    'profile_image_url': receiver_profile_url,
                } if exchange.receiver else None,
                'sender': {
                    'uid': str(exchange.sender.uid),
                    'name': exchange.sender.display_name,
                    'profession': exchange.sender.profession,
                    'city': exchange.sender.city,
                    'country': exchange.sender.country,
                    'profile_image_url': sender_profile_url,
                } if exchange.sender else None,
            }
        
        elif activity.activity_type == 'song_discovery' and activity.song:
            song = activity.song
            activity_data['song'] = {
                'uid': str(song.uid),
                'title': song.title,
                'artist': song.artist,
                'url': song.url,
                'cover_image_url': song.cover_image_url,
                'genre': song.genre,
            }
        
        feed_data.append(activity_data)
    
    logger.info(f"Returning {len(feed_data)} activities to {user.email}")
    
    return Response({
        'count': len(feed_data),
        'activities': feed_data,
        'scope': scope
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@handle_api_errors
def activity_debug(request):
    """
    Debug endpoint to check activity creation
    Returns statistics about activities in the system
    """
    user = request.user
    
    total_activities = Activity.objects.count()
    user_activities = Activity.objects.filter(actor=user).count()
    discovery_activities = Activity.objects.filter(activity_type='song_discovery').count()
    exchange_activities = Activity.objects.filter(activity_type='song_exchange').count()
    recent_activities = Activity.objects.order_by('-created_at')[:10]
    
    recent_list = []
    for activity in recent_activities:
        recent_list.append({
            'uid': str(activity.uid),
            'type': activity.activity_type,
            'actor': activity.actor.email,
            'created_at': activity.created_at.isoformat(),
            'has_song': activity.song is not None,
            'has_exchange': activity.song_exchange is not None,
        })
    
    return Response({
        'total_activities': total_activities,
        'user_activities': user_activities,
        'discovery_activities': discovery_activities,
        'exchange_activities': exchange_activities,
        'recent_activities': recent_list,
    })

