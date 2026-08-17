# KizukaPay Landing Page

A modern, responsive landing page for KizukaPay - Payment Infrastructure for African Sportsbooks.

## Features

The landing page includes all 10 sections as designed:

1. **Hero Section** - Main headline with CTA buttons and supported payment methods
2. **Product Preview** - Dashboard overview with key features
3. **How It Works** - 3-step process visualization
4. **Infrastructure Features** - 6-card feature grid
5. **African Market Section** - Market statistics and information
6. **Partners Section** - Partner categories showcase
7. **Developer Section** - Developer-first infrastructure features
8. **Security Section** - Security highlights
9. **Call To Action** - Final conversion section
10. **Footer** - Company links and contact information

## Design System

### Colors
- **Primary Dark**: Navy background (`#0f172e`)
- **Primary Navy**: Secondary background (`#1a2847`)
- **Electric Blue**: Primary accent (`#00d4ff`)
- **Neon Blue**: Secondary accent (`#0096ff`)
- **Accent Purple**: Tertiary accent (`#7c3aed`)
- **Success Green**: Status indicator (`#10b981`)

### Typography
- **Headlines**: Space Grotesk (700 weight)
- **Body**: Inter (400-600 weight)
- **UI**: Space Grotesk (600-700 weight)

### Effects
- Gradient overlays and glassmorphism
- Glow animations on hero section
- Hover animations on cards and buttons
- Smooth scroll behavior
- Parallax effects on hero visual

## File Structure

```
landing/
├── __init__.py                          # App initialization
├── admin.py                             # Django admin configuration
├── apps.py                              # App configuration
├── models.py                            # Database models (empty)
├── tests.py                             # Test cases
├── views.py                             # View logic
├── urls.py                              # URL routing
├── templates/
│   └── landing.html                     # Main landing page template
└── static/
    ├── css/
    │   └── landing.css                  # Main stylesheet
    └── js/
        └── landing.js                   # Client-side interactivity
```

## Views & URLs

### Views
- `LandingPageView` - Renders the landing page template

### URL Patterns
- `/` - Landing page home

## Installation

The landing page is already integrated into the KizukaPay project. To use it:

1. The `landing` app has been added to `INSTALLED_APPS` in `core/settings.py`
2. The landing URLs have been included in `core/urls.py`
3. Run migrations (if any models are added in the future):
   ```bash
   python manage.py migrate
   ```

## Development

### Running the Development Server
```bash
python manage.py runserver
```

The landing page will be available at `http://localhost:8000/`

### Static Files
To collect static files for production:
```bash
python manage.py collectstatic
```

## Customization

### Updating Content
Edit `landing/templates/landing.html` to modify:
- Headlines and subheadings
- Feature descriptions
- Button labels and links
- Footer information

### Styling Changes
Edit `landing/static/css/landing.css` to modify:
- Colors (update CSS variables at the top)
- Typography and font sizes
- Spacing and padding
- Animations and transitions
- Responsive breakpoints

### Adding Interactivity
Edit `landing/static/js/landing.js` to add:
- Button click handlers
- Form submissions
- Analytics tracking
- Additional animations

### Adding Images
1. Create a `landing/static/images/` directory
2. Add your images there
3. Reference them in templates as `{% static 'images/filename.svg' %}`

## Button Linking

The template includes smart button handlers:

- **"Request Integration"** → Links to `/dashboard/`
- **"View Dashboard"** → Links to `/dashboard/`
- **"View API Docs"** → Opens external API documentation
- **"Start Partnership"** → Opens mailto to support@kizukapay.com
- **"Contact Support"** → Opens mailto to support@kizukapay.com

Modify these in `landing/static/js/landing.js` in the button click handler section.

## Responsive Design

The landing page is fully responsive with breakpoints at:
- **768px and below** - Tablet/Large mobile layout
- **480px and below** - Small mobile layout

Responsive CSS handles:
- Grid layout adjustments
- Font size scaling
- Navigation restructuring
- Button stack vertically on small screens

## Performance Features

- Intersection Observer for lazy loading animations
- Parallax scrolling effects
- GPU-accelerated transforms
- Optimized CSS animations
- Minimal JavaScript dependencies

## Browser Compatibility

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Mobile browsers (iOS Safari 14+, Chrome Android)

## Future Enhancements

Consider adding:
- Newsletter signup form
- Live partner logos integration
- Dashboard screenshot/video
- Customer testimonials section
- Blog integration
- Analytics tracking
- A/B testing for CTA buttons
- Chat support widget

## Support

For questions or issues with the landing page, refer to:
1. The HTML structure in `landing/templates/landing.html`
2. CSS variables and styles in `landing/static/css/landing.css`
3. JavaScript interactivity in `landing/static/js/landing.js`

---

Built with ❤️ for KizukaPay
