from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter

geolocator = Nominatim(user_agent="clinic_locator")
geocode = RateLimiter(geolocator.geocode, min_delay_seconds=1)

def get_lat_lng_from_address(address):
    if not address:
        return None, None

    location = geocode(address)
    if location:
        return location.latitude, location.longitude

    return None, None
