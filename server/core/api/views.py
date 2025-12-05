from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from django.contrib.auth import get_user_model
from core.models import Activity, ActivityReaction, ActivityComment
from django.db.models import Count
from users.models import Friendship
import pycountry

User = get_user_model()


@api_view(["GET"])
def country_list(request):
    search = request.GET.get("search", "").lower()
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


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def activity_feed(request):
    """
    Get activity feed from friends or all users
    Query parameter: ?scope=friends (default) or ?scope=all
    Shows song exchanges and discoveries
    """
    user = request.user
    scope = request.GET.get('scope', 'friends')  # 'friends' or 'all'
    
    if scope == 'all':
        # Get activities from all users (excluding current user)
        activities = Activity.objects.exclude(
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
        ).order_by('-created_at')[:50]  # Limit to 50 most recent
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
        
        # Get activities from friends
        activities = Activity.objects.filter(
            actor_id__in=friend_ids
        ).select_related(
        'actor',
        'song',
        'song_exchange',
        'song_exchange__sent_song',
        'song_exchange__received_song',
        'song_exchange__sender',
        'song_exchange__receiver',
        'song__platform'
    ).order_by('-created_at')[:50]  # Limit to 50 most recent
    
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
        comments_data = []
        try:
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
            'comments_count': ActivityComment.objects.filter(activity=activity).count(),
        }
        
        if activity.activity_type == 'song_exchange' and activity.song_exchange:
            exchange = activity.song_exchange
            activity_data['exchange'] = {
                'uid': str(exchange.uid),
                'sent_song': {
                    'uid': str(exchange.sent_song.uid),
                    'title': exchange.sent_song.title,
                    'artist': exchange.sent_song.artist,
                    'url': exchange.sent_song.url,
                    'cover_image_url': exchange.sent_song.cover_image_url,
                } if exchange.sent_song else None,
                'received_song': {
                    'uid': str(exchange.received_song.uid),
                    'title': exchange.received_song.title,
                    'artist': exchange.received_song.artist,
                    'url': exchange.received_song.url,
                    'cover_image_url': exchange.received_song.cover_image_url,
                } if exchange.received_song else None,
                'receiver': {
                    'uid': str(exchange.receiver.uid),
                    'name': exchange.receiver.display_name,
                } if exchange.receiver else None,
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
    
    return Response({
        'count': len(feed_data),
        'activities': feed_data,
        'scope': scope
    })

