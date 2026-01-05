from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from core.models import Activity, ActivityReaction, ActivityComment
from music.models import SongExchange
from core.decorators import handle_api_errors, validate_uuid
from core.notification import send_notification
import logging

logger = logging.getLogger(__name__)


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
@handle_api_errors
@validate_uuid('activity_id')
def toggle_reaction(request, activity_id, reaction_type):
    """
    Toggle a reaction to an activity (add if not exists, remove if exists)
    POST: Toggle reaction (add if not exists, remove if exists)
    DELETE: Remove reaction (for backward compatibility)
    """
    try:
        activity = Activity.objects.get(uid=activity_id)
    except Activity.DoesNotExist:
        logger.warning(f"Activity {activity_id} not found for user {request.user.email}")
        return Response(
            {'error': 'Activity not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"Error fetching activity {activity_id}: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Invalid activity ID'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user
    
    # Validate reaction type
    valid_reactions = ['🎵', '🎶', '🎸', '🎹', '🥁', '🎤']
    if not reaction_type or reaction_type not in valid_reactions:
        logger.warning(f"Invalid reaction type '{reaction_type}' from user {user.email}")
        return Response(
            {'error': 'Invalid reaction type. Must be one of: 🎵, 🎶, 🎸, 🎹, 🥁, 🎤'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if reaction already exists
    existing_reaction = ActivityReaction.objects.filter(
        user=user,
        activity=activity,
        reaction_type=reaction_type
    ).first()
    
    if request.method == 'POST':
        # Toggle: if exists, remove it; if not, add it
        if existing_reaction:
            # Remove reaction
            existing_reaction.delete()
            return Response({
                'message': 'Reaction removed',
                'reaction_type': reaction_type,
                'action': 'removed'
            }, status=status.HTTP_200_OK)
        else:
            # Add reaction
            ActivityReaction.objects.create(
                user=user,
                activity=activity,
                reaction_type=reaction_type
            )
            
            # Send notifications to activity participants (only when adding, not removing)
            try:
                activity_url = f"/feed?activity={str(activity.uid)}"
                
                # Notify the activity actor (the person who created the activity)
                if activity.actor and activity.actor != user:
                    send_notification(
                        sender=user,
                        recipient=activity.actor,
                        verb='liked',
                        action_object=None,
                        target=activity,
                        description=f'{user.display_name} liked your activity',
                        send_push=False,
                        target_url=activity_url
                    )
                    logger.info(f"Notification sent to activity actor {activity.actor.email} for reaction on activity {activity.uid}")
                
                # For song exchanges, also notify the other party (receiver)
                if activity.activity_type == 'song_exchange' and activity.song_exchange:
                    exchange = activity.song_exchange
                    # Notify receiver if they're different from actor and person who reacted
                    if exchange.receiver and exchange.receiver != user and exchange.receiver != activity.actor:
                        send_notification(
                            sender=user,
                            recipient=exchange.receiver,
                            verb='liked',
                            action_object=None,
                            target=activity,
                            description=f'{user.display_name} liked the song exchange',
                            send_push=False,
                            target_url=activity_url
                        )
                        logger.info(f"Notification sent to receiver {exchange.receiver.email} for reaction on activity {activity.uid}")
                    
                    # Notify sender if they're different from actor and person who reacted
                    if exchange.sender and exchange.sender != user and exchange.sender != activity.actor:
                        send_notification(
                            sender=user,
                            recipient=exchange.sender,
                            verb='liked',
                            action_object=None,
                            target=activity,
                            description=f'{user.display_name} liked the song exchange',
                            send_push=False,
                            target_url=activity_url
                        )
                        logger.info(f"Notification sent to sender {exchange.sender.email} for reaction on activity {activity.uid}")
            except Exception as e:
                logger.error(f"Error sending reaction notifications: {str(e)}", exc_info=True)
                # Don't fail the reaction creation if notification fails
            
            return Response({
                'message': 'Reaction added',
                'reaction_type': reaction_type,
                'action': 'added'
            }, status=status.HTTP_201_CREATED)
    
    elif request.method == 'DELETE':
        # Remove reaction (for backward compatibility)
        if not existing_reaction:
            return Response(
                {'error': 'Reaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        existing_reaction.delete()
        return Response({
            'message': 'Reaction removed',
            'action': 'removed'
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@handle_api_errors
@validate_uuid('activity_id')
def get_activity_reactions(request, activity_id):
    """
    Get all reactions for an activity
    """
    try:
        activity = Activity.objects.get(uid=activity_id)
    except Activity.DoesNotExist:
        return Response(
            {'error': 'Activity not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    reactions = ActivityReaction.objects.filter(
        activity=activity
    ).select_related('user').order_by('-created_at')
    
    reactions_summary = {}
    for reaction in reactions:
        reaction_type = reaction.reaction_type
        if reaction_type not in reactions_summary:
            reactions_summary[reaction_type] = {
                'count': 0,
                'users': []
            }
        reactions_summary[reaction_type]['count'] += 1
        if len(reactions_summary[reaction_type]['users']) < 10:
            reactions_summary[reaction_type]['users'].append({
                'uid': str(reaction.user.uid),
                'name': reaction.user.display_name,
            })
    
    return Response({
        'reactions': reactions_summary
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@handle_api_errors
@validate_uuid('activity_id')
def add_comment(request, activity_id):
    """
    Add a comment to an activity
    """
    try:
        activity = Activity.objects.get(uid=activity_id)
    except Activity.DoesNotExist:
        return Response(
            {'error': 'Activity not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    user = request.user
    
    # Input validation
    text = request.data.get('text', '').strip()
    
    if not text:
        logger.warning(f"Empty comment attempt by {user.email} on activity {activity_id}")
        return Response(
            {'error': 'Comment text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(text) > 500:
        logger.warning(f"Comment too long ({len(text)} chars) by {user.email} on activity {activity_id}")
        return Response(
            {'error': 'Comment is too long (max 500 characters)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # For song exchanges, we need to ensure comments are visible to both parties
        # Since there are two activities (one for each direction of the exchange),
        # we'll create the comment on the requested activity, but the get_activity_comments
        # endpoint will aggregate comments from both related activities
        comment = ActivityComment.objects.create(
            user=user,
            activity=activity,
            text=text
        )
        logger.info(f"Comment {comment.uid} created by {user.email} on activity {activity_id}")
        
        # Log if there's a reciprocal activity for debugging
        if activity.activity_type == 'song_exchange' and activity.song_exchange:
            exchange = activity.song_exchange
            if exchange.sender and exchange.receiver and exchange.sent_song and exchange.received_song:
                reciprocal_exchange = SongExchange.objects.filter(
                    sender=exchange.receiver,
                    receiver=exchange.sender,
                    sent_song=exchange.received_song,
                    received_song=exchange.sent_song,
                    status='matched'
                ).first()
                if reciprocal_exchange:
                    reciprocal_activities = Activity.objects.filter(
                        song_exchange=reciprocal_exchange,
                        activity_type='song_exchange'
                    )
                    logger.info(
                        f"Found {reciprocal_activities.count()} reciprocal activities for exchange {exchange.uid}. "
                        f"Comments will be aggregated when fetching."
                    )
        
        # Send notifications to activity participants
        try:
            # Prepare activity URL for navigation
            activity_url = f"/feed?activity={str(activity.uid)}"
            
            # Notify the activity actor (the person who created the activity)
            if activity.actor and activity.actor != user:
                send_notification(
                    sender=user,
                    recipient=activity.actor,
                    verb='commented_on',
                    action_object=comment,
                    target=activity,
                    description=f'{user.display_name} commented on your activity',
                    send_push=False,
                    target_url=activity_url
                )
                logger.info(f"Notification sent to activity actor {activity.actor.email} for comment {comment.uid}")
            
            # For song exchanges, also notify the other party (receiver)
            if activity.activity_type == 'song_exchange' and activity.song_exchange:
                exchange = activity.song_exchange
                # Notify receiver if they're different from actor and commenter
                if exchange.receiver and exchange.receiver != user and exchange.receiver != activity.actor:
                    send_notification(
                        sender=user,
                        recipient=exchange.receiver,
                        verb='commented_on',
                        action_object=comment,
                        target=activity,
                        description=f'{user.display_name} commented on the song exchange',
                        send_push=False,
                        target_url=activity_url
                    )
                    logger.info(f"Notification sent to receiver {exchange.receiver.email} for comment {comment.uid}")
                
                # Notify sender if they're different from actor and commenter
                if exchange.sender and exchange.sender != user and exchange.sender != activity.actor:
                    send_notification(
                        sender=user,
                        recipient=exchange.sender,
                        verb='commented_on',
                        action_object=comment,
                        target=activity,
                        description=f'{user.display_name} commented on the song exchange',
                        send_push=False,
                        target_url=activity_url
                    )
                    logger.info(f"Notification sent to sender {exchange.sender.email} for comment {comment.uid}")
        except Exception as e:
            logger.error(f"Error sending comment notifications: {str(e)}", exc_info=True)
            # Don't fail the comment creation if notification fails
        
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to create comment'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    profile_image_url = None
    if user.profile_image:
        try:
            profile_image_url = request.build_absolute_uri(user.profile_image.url)
        except:
            pass
    
    return Response({
        'uid': str(comment.uid),
        'user': {
            'uid': str(user.uid),
            'name': user.display_name,
            'profile_image_url': profile_image_url,
        },
        'text': comment.text,
        'created_at': comment.created_at.isoformat(),
    }, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
@handle_api_errors
@validate_uuid('activity_id')
def get_activity_comments(request, activity_id):
    """
    Get all comments for an activity
    For song exchanges, also include comments from the reciprocal activity
    (since there are two activities for bidirectional exchanges)
    """
    try:
        activity = Activity.objects.get(uid=activity_id)
    except Activity.DoesNotExist:
        return Response(
            {'error': 'Activity not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # For song exchanges, get comments from both activities (original and reciprocal)
    # This ensures both users see all comments regardless of which activity they're viewing
    if activity.activity_type == 'song_exchange' and activity.song_exchange:
        exchange = activity.song_exchange
        
        # Find the reciprocal exchange (same songs, swapped sender/receiver)
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
        
        # Get all comments from all related activities
        comments = ActivityComment.objects.filter(
            activity_id__in=activity_ids
        ).select_related('user', 'activity').order_by('created_at')
        
        logger.info(
            f"Fetching comments for activity {activity_id} (exchange {exchange.uid}) "
            f"by user {request.user.email}. Found {comments.count()} comments "
            f"across {len(activity_ids)} related activities"
        )
    else:
        # For non-exchange activities, just get comments for this activity
        comments = ActivityComment.objects.filter(
            activity=activity
        ).select_related('user').order_by('created_at')
        
        logger.info(
            f"Fetching comments for activity {activity_id} (type: {activity.activity_type}) "
            f"by user {request.user.email}. Found {comments.count()} comments"
        )
    
    comments_data = []
    seen_comment_ids = set()  # Deduplicate in case of any overlap
    
    for comment in comments:
        # Skip duplicates (shouldn't happen, but safety check)
        if comment.uid in seen_comment_ids:
            continue
        seen_comment_ids.add(comment.uid)
        
        profile_image_url = None
        if comment.user.profile_image:
            try:
                profile_image_url = request.build_absolute_uri(comment.user.profile_image.url)
            except:
                pass
        
        comments_data.append({
            'uid': str(comment.uid),
            'user': {
                'uid': str(comment.user.uid),
                'name': comment.user.display_name,
                'profile_image_url': profile_image_url,
            },
            'text': comment.text,
            'created_at': comment.created_at.isoformat(),
        })
        
        logger.debug(
            f"Comment {comment.uid} by {comment.user.email} ({comment.user.display_name}) "
            f"on activity {comment.activity.uid}: '{comment.text[:50]}...'"
        )
    
    logger.info(
        f"Returning {len(comments_data)} unique comments for activity {activity_id} to user {request.user.email}"
    )
    
    return Response({
        'count': len(comments_data),
        'comments': comments_data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@handle_api_errors
@validate_uuid('comment_id')
def delete_comment(request, comment_id):
    """
    Delete a comment (only by the comment author)
    """
    try:
        comment = ActivityComment.objects.get(uid=comment_id)
    except ActivityComment.DoesNotExist:
        return Response(
            {'error': 'Comment not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    if comment.user != request.user:
        logger.warning(f"User {request.user.email} attempted to delete comment {comment_id} owned by {comment.user.email}")
        return Response(
            {'error': 'You can only delete your own comments'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        comment.delete()
        logger.info(f"Comment {comment_id} deleted by {request.user.email}")
        return Response({
            'message': 'Comment deleted'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Failed to delete comment'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

