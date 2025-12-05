from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from core.models import Activity, ActivityReaction


@api_view(['POST', 'DELETE'])
@permission_classes([IsAuthenticated])
def toggle_reaction(request, activity_id, reaction_type):
    """
    Add or remove a reaction to an activity
    POST: Add reaction
    DELETE: Remove reaction
    """
    activity = get_object_or_404(Activity, uid=activity_id)
    user = request.user
    
    # Validate reaction type
    valid_reactions = ['🎵', '🎶', '🎸', '🎹', '🥁', '🎤']
    if reaction_type not in valid_reactions:
        return Response(
            {'error': 'Invalid reaction type'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if request.method == 'POST':
        # Add reaction
        reaction, created = ActivityReaction.objects.get_or_create(
            user=user,
            activity=activity,
            reaction_type=reaction_type,
            defaults={}
        )
        
        if not created:
            return Response(
                {'error': 'Reaction already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return Response({
            'message': 'Reaction added',
            'reaction_type': reaction_type
        }, status=status.HTTP_201_CREATED)
    
    elif request.method == 'DELETE':
        # Remove reaction
        reaction = ActivityReaction.objects.filter(
            user=user,
            activity=activity,
            reaction_type=reaction_type
        ).first()
        
        if not reaction:
            return Response(
                {'error': 'Reaction not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        reaction.delete()
        return Response({
            'message': 'Reaction removed'
        }, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_activity_reactions(request, activity_id):
    """
    Get all reactions for an activity
    """
    activity = get_object_or_404(Activity, uid=activity_id)
    
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
def add_comment(request, activity_id):
    """
    Add a comment to an activity
    """
    activity = get_object_or_404(Activity, uid=activity_id)
    user = request.user
    
    text = request.data.get('text', '').strip()
    
    if not text:
        return Response(
            {'error': 'Comment text is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(text) > 500:
        return Response(
            {'error': 'Comment is too long (max 500 characters)'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    comment = ActivityComment.objects.create(
        user=user,
        activity=activity,
        text=text
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
def get_activity_comments(request, activity_id):
    """
    Get all comments for an activity
    """
    activity = get_object_or_404(Activity, uid=activity_id)
    
    comments = ActivityComment.objects.filter(
        activity=activity
    ).select_related('user').order_by('created_at')
    
    comments_data = []
    for comment in comments:
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
    
    return Response({
        'count': len(comments_data),
        'comments': comments_data
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_comment(request, comment_id):
    """
    Delete a comment (only by the comment author)
    """
    comment = get_object_or_404(ActivityComment, uid=comment_id)
    
    if comment.user != request.user:
        return Response(
            {'error': 'You can only delete your own comments'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    comment.delete()
    return Response({
        'message': 'Comment deleted'
    }, status=status.HTTP_200_OK)

