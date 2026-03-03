from django.shortcuts import render

# Create your views here.

def overview_view(request):
    """Dashboard overview page"""
    return render(request, "overview.html", {})