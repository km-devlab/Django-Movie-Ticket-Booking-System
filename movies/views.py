# Import the function at the top of views.py
from movies.services import send_booking_confirmation_email
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import render, redirect ,get_object_or_404
from .models import Movie,Theater,Seat,Booking, Genre, Language
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError

MOVIE_SORTS = {
    "name": ("Name A-Z", "name"),
    "rating": ("Top rated", "-rating"),
    "newest": ("Newest", "-id"),
}


def _apply_movie_filters(queryset, search_query=None, genres=None, languages=None):
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(cast__icontains=search_query)
        )
    if genres:
        queryset = queryset.filter(genres__slug__in=genres)
    if languages:
        queryset = queryset.filter(languages__slug__in=languages)
    return queryset.distinct()


def _query_string(request, **overrides):
    params = request.GET.copy()
    for key, value in overrides.items():
        if value is None:
            params.pop(key, None)
        else:
            params[key] = value
    return params.urlencode()


def movie_list(request):
    search_query = request.GET.get('search', '').strip()
    selected_genres = [slug for slug in request.GET.getlist('genre') if slug]
    selected_languages = [slug for slug in request.GET.getlist('language') if slug]
    sort_key = request.GET.get('sort', 'name')
    if sort_key not in MOVIE_SORTS:
        sort_key = 'name'

    movies_for_genre_counts = _apply_movie_filters(
        Movie.objects.all(),
        search_query=search_query,
        languages=selected_languages,
    )
    movies_for_language_counts = _apply_movie_filters(
        Movie.objects.all(),
        search_query=search_query,
        genres=selected_genres,
    )
    movies = _apply_movie_filters(
        Movie.objects.prefetch_related('genres', 'languages'),
        search_query=search_query,
        genres=selected_genres,
        languages=selected_languages,
    ).order_by(MOVIE_SORTS[sort_key][1], 'id')

    genres = Genre.objects.annotate(
        movie_count=Count(
            'movies',
            filter=Q(movies__in=movies_for_genre_counts),
            distinct=True,
        )
    )
    languages = Language.objects.annotate(
        movie_count=Count(
            'movies',
            filter=Q(movies__in=movies_for_language_counts),
            distinct=True,
        )
    )

    paginator = Paginator(movies, 12)
    page_obj = paginator.get_page(request.GET.get('page'))
    sort_options = [
        {
            'key': key,
            'label': label,
        }
        for key, (label, ordering) in MOVIE_SORTS.items()
    ]

    context = {
        'movies': page_obj.object_list,
        'page_obj': page_obj,
        'paginator': paginator,
        'genres': genres,
        'languages': languages,
        'selected_genres': selected_genres,
        'selected_languages': selected_languages,
        'search_query': search_query,
        'sort_key': sort_key,
        'sort_label': MOVIE_SORTS[sort_key][0],
        'sort_options': sort_options,
        'total_movies': paginator.count,
        'page_query': _query_string(request, page=None),
    }
    return render(request,'movies/movie_list.html',context)

def theater_list(request,movie_id):
    movie = get_object_or_404(Movie,id=movie_id)
    theater=Theater.objects.filter(movie=movie)
    return render(request,'movies/theater_list.html',{'movie':movie,'theaters':theater})



@login_required(login_url='/login/')
def book_seats(request, theater_id):
    theater = get_object_or_404(Theater, id=theater_id)
    seats = Seat.objects.filter(theater=theater)
    if request.method == 'POST':
        selected_seats = request.POST.getlist('seats')
        error_seats = []
        if not selected_seats:
            return render(request, "movies/seat_selection.html", {'theater': theater, "seats": seats, 'error': "No seat selected"})
        
        new_booking_ids = []
        booked_seat_names = []  # To collect names for the email template
        
        for seat_id in selected_seats:
            seat = get_object_or_404(Seat, id=seat_id, theater=theater)
            if seat.is_booked:
                error_seats.append(seat.seat_number)
                continue
            try:
                booking = Booking.objects.create(
                    user=request.user,
                    seat=seat,
                    movie=theater.movie,
                    theater=theater
                )
                new_booking_ids.append(booking.id)
                booked_seat_names.append(seat.seat_number)  # Add seat number (e.g., "A1")
                seat.is_booked = True
                seat.save()
            except IntegrityError:
                error_seats.append(seat.seat_number)
                
        if error_seats:
            error_message = f"The following seats are already booked: {', '.join(error_seats)}"
            return render(request, 'movies/seat_selection.html', {'theater': theater, "seats": seats, 'error': error_message})
        
        # --- NEW DYNAMIC EMAIL TRIGGER ---
        if new_booking_ids:
            # 1. Prepare dynamic layout data from the booking session
            email_context = {
                'show_title': theater.movie.name,
                'show_timing': getattr(theater, 'timing', 'Check dashboard for timing'), # Fallback if timing field name differs
                'seat_numbers': ", ".join(booked_seat_names),
                'theater_info': f"{theater.name}, {theater.location if hasattr(theater, 'location') else ''}",
                'payment_id': f"BKS-{new_booking_ids[0]}" # Fallback tracking ID using the primary booking reference
            }
            
            # 2. Fire the service function directly
            send_booking_confirmation_email(request.user.email, email_context)
            
        return redirect('profile')
    return render(request, 'movies/seat_selection.html', {'theater': theater, "seats": seats})


def home(request):
    movies = Movie.objects.all()
    return render(request, 'home.html', {'movies': movies})

from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
from .models import Seat, Booking

@user_passes_test(lambda u: u.is_superuser)  # Only lets you run this if you are logged in as admin
def emergency_database_reset(request):
    try:
        # Delete all bookings and unlock all seats
        Booking.objects.all().delete()
        Seat.objects.all().update(is_booked=False)
        return HttpResponse("🚀 [SUCCESS] Live database fully reset to original state!")
    except Exception as e:
        return HttpResponse(f"❌ [ERROR] Reset failed: {str(e)}", status=500)

