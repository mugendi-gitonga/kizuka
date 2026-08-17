# KizukaPay Landing Page - Tailwind CSS & DaisyUI Setup Guide

## Quick Start

### 1. Install Dependencies
```bash
npm install
# or
yarn install
```

### 2. Build Tailwind CSS
```bash
# One-time build
npm run tailwind

# Watch mode (for development)
npm run tailwind:watch
```

### 3. Run Django Server
```bash
python manage.py runserver
```

Visit: `http://localhost:8000/`

---

## Project Structure

```
landing/
├── templates/
│   └── landing.html              # Main template with Tailwind classes
├── static/
│   ├── css/
│   │   ├── input.css            # Tailwind input file
│   │   └── output.css           # Generated compiled CSS
│   ├── js/
│   │   └── landing.js           # JavaScript interactivity
│   └── images/
│       ├── dashboard-mockup.svg  # Hero dashboard visual
│       ├── africa-market-map.svg # Africa market map
│       └── payment-flow.svg      # Payment methods flow
├── views.py                      # Django view for landing page
├── urls.py                       # URL routing
├── apps.py                       # App configuration
└── README.md                     # App documentation
```

---

## Mobile Responsiveness Features

The landing page is fully responsive with Tailwind's mobile-first approach:

### Breakpoints Used
- **Mobile**: < 640px (sm)
- **Tablet**: ≥ 768px (md)
- **Desktop**: ≥ 1024px (lg)

### Key Mobile Features

#### 1. Navigation
- Hidden desktop menu on mobile
- Mobile hamburger menu with dropdown
- Sticky navbar with backdrop blur

```html
<!-- Desktop menu (hidden on mobile) -->
<div class="hidden md:flex gap-6">
  <a href="#product">PRODUCT</a>
</div>

<!-- Mobile menu (visible only on mobile) -->
<div class="dropdown dropdown-end md:hidden">
  ...hamburger menu...
</div>
```

#### 2. Hero Section
- Single column layout on mobile
- Two column grid on desktop
- Responsive typography (4xl → 6xl)
- Flexible button layout (column → row)

```html
<div class="grid grid-cols-1 md:grid-cols-2 gap-8 md:gap-12">
  <!-- Stacks vertically on mobile, side-by-side on desktop -->
</div>
```

#### 3. Feature Grid
- 1 column on mobile (sm:grid-cols-2)
- 2 columns on tablets (lg:grid-cols-3)
- 3 columns on desktop

```html
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
```

#### 4. Typography Scaling
- Responsive font sizes using Tailwind's responsive prefixes
- Example: `text-3xl md:text-4xl` (scales from 30px to 36px)

#### 5. Spacing
- Adaptive padding: `px-4 md:px-8` (16px → 32px)
- Adaptive gaps: `gap-4 md:gap-8`
- Adaptive margins: `mb-12 md:mb-16`

#### 6. Hidden Elements
- Hero visual hidden on mobile: `hidden md:flex`
- Mobile nav hidden on desktop: `hidden md:hidden` → `dropdown-end md:hidden`

### Mobile-First Development

All Tailwind utilities are mobile-first. This means:
- Base style applies to all
- `md:` prefix applies to medium screens and up
- `lg:` prefix applies to large screens and up

Example:
```html
<div class="px-4 md:px-8 lg:px-12">
  <!-- 16px on mobile, 32px on tablet+, 48px on desktop+ -->
</div>
```

---

## Color System

The landing page uses a custom DaisyUI theme "kizuka":

### CSS Variables (in tailwind.config.js)
```javascript
colors: {
  primary: {
    dark: '#0f172e',      // Navy backgrounds
    navy: '#1a2847',      // Secondary navy
    secondary: '#2d3f6e', // Elevated backgrounds
  },
  accent: {
    blue: '#00d4ff',      // Electric cyan (PRIMARY)
    neon: '#0096ff',      // Neon blue
    purple: '#7c3aed',    // Purple accents
  },
  text: {
    light: '#ffffff',         // Main text
    secondary: '#b0b8d4',     // Secondary text
    tertiary: '#8892b0',      // Tertiary text
  },
}
```

### Using Colors in Classes
- Primary button: `btn-primary` (cyan)
- Secondary button: `btn-secondary` (outline)
- Text colors: `text-white`, `text-blue-200`, `text-blue-300`
- Background: `bg-slate-900`, `bg-slate-950`
- Borders: `border-blue-500/10` (10% opacity)

---

## Tailwind CSS Utilities

### Common Patterns in Landing Page

**Gradient Text**
```html
<h1 class="gradient-text">
  Payment Infrastructure for African Sportsbooks
</h1>
```

**Glow Box** (Custom)
```html
<div class="glow-box p-8 space-y-4">
  <!-- Content -->
</div>
```

**Button Styling**
```html
<button class="btn btn-primary btn-lg rounded-lg shadow-lg shadow-cyan-500/50">
  Request Integration
</button>
```

**Flex Containers**
```html
<!-- Flex with responsive direction -->
<div class="flex flex-col sm:flex-row gap-4">
  <!-- Vertical on mobile, horizontal on tablet+ -->
</div>
```

**Grid Layouts**
```html
<!-- Auto-responsive grid -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
```

---

## DaisyUI Components Used

The landing page utilizes these DaisyUI components:

### Navbar
```html
<nav class="navbar">
  <div class="flex-1">...</div>
  <div class="flex-none">...</div>
</nav>
```

### Buttons
```html
<button class="btn btn-primary">Primary</button>
<button class="btn btn-secondary">Secondary</button>
<button class="btn btn-outline">Outline</button>
```

### Badge
```html
<span class="badge badge-lg badge-outline badge-primary">MPESA</span>
```

### Dropdown
```html
<div class="dropdown dropdown-end">
  <button class="btn btn-ghost btn-circle">Menu</button>
  <ul class="dropdown-content menu">
    <li><a href="#">Option</a></li>
  </ul>
</div>
```

---

## Custom Animations

### Available Animations

**Float Animation** (Hero visual)
```css
@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-20px); }
}

.animate-float { animation: float 6s ease-in-out infinite; }
```

Usage:
```html
<div class="animate-float">Floating Element</div>
```

**Glow Effect** (Cards)
```css
/* Applied via CSS with box-shadow animation */
```

---

## Testing Mobile Responsiveness

### In Browser DevTools

1. Open landing page in Chrome/Firefox
2. Press `F12` to open DevTools
3. Click **Toggle Device Toolbar** (or Ctrl+Shift+M)
4. Test common device sizes:
   - iPhone 12: 390x844px
   - iPad: 768x1024px
   - Desktop: 1920x1080px

### Key Areas to Test

- ✅ Navigation menu collapses on mobile
- ✅ Hero section stacks vertically on mobile
- ✅ Feature grid adapts to device width
- ✅ Images scale responsively
- ✅ Text remains readable
- ✅ Buttons are touch-friendly (min 44x44px)
- ✅ No horizontal scrolling on mobile
- ✅ Spacing adapts to screen size

### Viewport Meta Tag
```html
<meta name="viewport" content="width=device-width, initial-scale=1.0">
```

---

## CSS File Compilation

### Two CSS Files

1. **input.css** - Your custom Tailwind directives
   - Contains @tailwind directives
   - Custom utilities defined with @layer
   - Located: `landing/static/css/input.css`

2. **output.css** - Generated Tailwind CSS
   - Auto-generated by Tailwind CLI
   - Contains all Tailwind utilities + your custom styles
   - This is what gets loaded in the HTML
   - Never edit manually

### Workflow

```bash
# Watch file changes and re-compile
npm run tailwind:watch

# This generates output.css automatically
```

---

## Performance Optimization

### PurgeCSS (Built-in)

Tailwind automatically removes unused CSS:

```javascript
// tailwind.config.js
content: [
  "./landing/templates/**/*.{html,js}",  // Scan these files
],
```

Only CSS classes found in your HTML are included in output.css.

### Benefits
- Smaller CSS file size
- Faster page loads
- Better performance

---

## Troubleshooting

### CSS Not Loading
1. Make sure `npm run tailwind:watch` is running
2. Check that `output.css` is generated in `landing/static/css/`
3. Clear Django cache: `python manage.py clear_cache`
4. Hard refresh browser: **Ctrl+Shift+R** (Windows) or **Cmd+Shift+R** (Mac)

### Styles Not Applied
1. Verify class names are spelled correctly (case-sensitive)
2. Check that Tailwind scans the right file paths in `tailwind.config.js`
3. Rebuild: `npm run tailwind`

### Mobile Menu Not Working
- Ensure DaisyUI JavaScript is loaded (included in CDN)
- Check browser console for errors

---

## Resources

- **Tailwind CSS Docs**: https://tailwindcss.com/docs
- **DaisyUI Docs**: https://daisyui.com/docs/
- **Responsive Design**: https://tailwindcss.com/docs/responsive-design

---

## Next Steps

1. **Generate Real Images**: Use the IMAGE_GENERATION_GUIDE.md for professional images
2. **Customize Colors**: Modify `tailwind.config.js` to match brand guidelines
3. **Add More Sections**: Extend the landing page with additional content
4. **SEO Optimization**: Add meta tags and structured data
5. **Analytics**: Integrate tracking for conversions

---

## Support

For issues or questions:
- Check Tailwind CSS documentation
- Review DaisyUI component library
- Test in different browsers and devices
- Verify responsive breakpoints are correct

Build beautiful, responsive UIs with Tailwind CSS! 🚀
