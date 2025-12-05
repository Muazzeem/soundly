from django.forms import model_to_dict
from notifications.utils import id2slug
from notifications.settings import get_config

def get_object_url(instance, notification, request):
    """
    Get url representing the instance object.
    This will return instance.get_url_for_notifications()
    with parameters `notification` and `request`,
    if it is defined and get_absolute_url() otherwise
    """
    if hasattr(instance, 'get_url_for_notifications'):
        return instance.get_url_for_notifications(notification, request)
    elif hasattr(instance, 'get_absolute_url'):
        return instance.get_absolute_url()
    return None

def get_num_to_fetch(request):
    default_num_to_fetch = get_config()['NUM_TO_FETCH']
    try:
        # If they don't specify, make it 5.
        num_to_fetch = request.GET.get('max', default_num_to_fetch)
        num_to_fetch = int(num_to_fetch)
        if not (1 <= num_to_fetch <= 100):
            num_to_fetch = default_num_to_fetch
    except ValueError:  # If casting to an int fails.
        num_to_fetch = default_num_to_fetch
    return num_to_fetch
