import csv
import datetime
from io import StringIO
from django.core.cache import cache
from django.db.models import Sum, Count, F, Q, FloatField, ExpressionWrapper
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncHour
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone

from movies.models import Booking, Movie, Theater

# Helper to get date range from request
def get_date_range(request):
    start = request.GET.get('start')
    end = request.GET.get('end')
    try:
        if start:
            start_date = datetime.datetime.strptime(start, "%Y-%m-%d").date()
        else:
            start_date = None
        if end:
            end_date = datetime.datetime.strptime(end, "%Y-%m-%d").date()
        else:
            end_date = None
    except ValueError:
        start_date = end_date = None
    return start_date, end_date

def filter_by_date(qs, start_date, end_date):
    if start_date:
        qs = qs.filter(booked_at__date__gte=start_date)
    if end_date:
        qs = qs.filter(booked_at__date__lte=end_date)
    return qs

@user_passes_test(lambda u: u.is_staff)
def dashboard(request):
    start_date, end_date = get_date_range(request)

    # Revenue aggregations (daily, weekly, monthly)
    # Directly compute without caching to always show latest bookings
    qs = Booking.objects.all()
    qs = filter_by_date(qs, start_date, end_date)
    daily = qs.annotate(day=TruncDay('booked_at')).values('day').annotate(total=Count('id')).order_by('day')
    weekly = qs.annotate(week=TruncWeek('booked_at')).values('week').annotate(total=Count('id')).order_by('week')
    monthly = qs.annotate(month=TruncMonth('booked_at')).values('month').annotate(total=Count('id')).order_by('month')
    # Debug total bookings across the selected range
    total_bookings = qs.count()
    revenue_data = {
        'daily': list(daily),
        'weekly': list(weekly),
        'monthly': list(monthly),
        'total_bookings': total_bookings,
    }
    
    # Popular movies
    movies_key = f"popular_movies_{start_date}_{end_date}"
    popular_movies = cache.get(movies_key)
    if not popular_movies:
        qs = Booking.objects.all()
        qs = filter_by_date(qs, start_date, end_date)
        popular_movies = list(
            qs.values('movie__name')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        cache.set(movies_key, popular_movies, 300)

    # Busiest theaters (occupancy rate)
    theaters_key = f"busiest_theaters_{start_date}_{end_date}"
    busiest_theaters = cache.get(theaters_key)
    if not busiest_theaters:
        qs = Booking.objects.select_related('theater')
        qs = filter_by_date(qs, start_date, end_date)
        # Assuming Theater model has a `capacity` field
        occupancy = qs.values('theater__name').annotate(
            booked=Count('id'),
            occupancy=Count('id')  # placeholder for occupancy rate
        )
        busiest_theaters = list(occupancy.order_by('-occupancy')[:10])
        cache.set(theaters_key, busiest_theaters, 300)

    # Peak booking hours
    hours_key = f"peak_hours_{start_date}_{end_date}"
    peak_hours = cache.get(hours_key)
    if not peak_hours:
        qs = Booking.objects.all()
        qs = filter_by_date(qs, start_date, end_date)
        peak_hours = list(
            qs.annotate(hour=TruncHour('booked_at'))
            .values('hour')
            .annotate(count=Count('id'))
            .order_by('-count')[:10]
        )
        cache.set(hours_key, peak_hours, 300)

    # Cancellation rate
    cancel_key = f"cancellation_rate_{start_date}_{end_date}"
    cancellation_rate = cache.get(cancel_key)
    if cancellation_rate is None:
        total = Booking.objects.all()
        total = filter_by_date(total, start_date, end_date)
        total_cnt = total.count()
        cancelled_cnt = 0  # No status field; placeholder
        cancellation_rate = (cancelled_cnt / total_cnt) if total_cnt else 0
        cache.set(cancel_key, cancellation_rate, 300)

    context = {
        'revenue': revenue_data,
        'popular_movies': popular_movies,
        'busiest_theaters': busiest_theaters,
        'peak_hours': peak_hours,
        'cancellation_rate': cancellation_rate,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'analytics/dashboard.html', context)

@user_passes_test(lambda u: u.is_staff)
def export_csv(request, report):
    # report can be: revenue_daily, revenue_weekly, revenue_monthly, movies, theaters, hours, cancellations
    start_date, end_date = get_date_range(request)
    # Reuse cached data where possible
    if report.startswith('revenue'):
        revenue = cache.get(f"revenue_{start_date}_{end_date}")
        if not revenue:
            return HttpResponse('No revenue data cached', status=400)
        period = report.split('_')[1]  # daily, weekly, monthly
        data = revenue.get(period, [])
        filename = f"revenue_{period}.csv"
        rows = [(item['day'] if period == 'daily' else (item['week'] if period == 'weekly' else item['month']), item['total']) for item in data]
    elif report == 'movies':
        data = cache.get(f"popular_movies_{start_date}_{end_date}") or []
        filename = "popular_movies.csv"
        rows = [(item['movie__name'], item['count']) for item in data]
    elif report == 'theaters':
        data = cache.get(f"busiest_theaters_{start_date}_{end_date}") or []
        filename = "busiest_theaters.csv"
        rows = [(item['theater__name'], item['occupancy']) for item in data]
    elif report == 'hours':
        data = cache.get(f"peak_hours_{start_date}_{end_date}") or []
        filename = "peak_hours.csv"
        rows = [(item['hour'], item['count']) for item in data]
    elif report == 'cancellations':
        rate = cache.get(f"cancellation_rate_{start_date}_{end_date}")
        filename = "cancellation_rate.csv"
        rows = [("cancellation_rate", rate)]
    else:
        return HttpResponse('Invalid report', status=400)

    # Generate CSV
    csv_file = StringIO()
    writer = csv.writer(csv_file)
    # Write header based on report type
    if report.startswith('revenue'):
        writer.writerow(['Period', 'Total Revenue'])
    elif report == 'movies':
        writer.writerow(['Movie Title', 'Bookings'])
    elif report == 'theaters':
        writer.writerow(['Theater Name', 'Occupancy Rate'])
    elif report == 'hours':
        writer.writerow(['Hour', 'Bookings'])
    elif report == 'cancellations':
        writer.writerow(['Metric', 'Value'])
    for row in rows:
        writer.writerow(row)

    response = HttpResponse(csv_file.getvalue(), content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response
