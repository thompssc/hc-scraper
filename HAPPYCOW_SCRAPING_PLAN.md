# HappyCow Scraping Plan for VeganVoyager
*Updated: 2024-12-19*

## Executive Summary

Based on comprehensive analysis of current HappyCow structure (2024), we can extract significantly more data than previously possible. The modern site embeds coordinates directly in Google Maps links and provides rich metadata through data attributes, JSON-LD structured data, and detailed venue information.

**Key Discovery**: Modern HappyCow (2024) embeds coordinates directly in Google Maps links on listing pages, eliminating the need for deep crawling that made the old method slow. This represents a ~10x performance improvement.

## Historical Context

### Old Method (HappyCowler - 2017)
- **Target**: `div.row.venue-list-item` elements
- **Major Limitation**: Required deep crawling to individual restaurant pages to get coordinates
- **Performance**: Slow due to deep crawling requirement
- **Data Quality**: Limited to basic info, ~60% coordinate coverage
- **Technology**: BeautifulSoup + requests with IncapSession for Incapsula protection

### Modern Method (2024)
- **Target**: `div.venue-list-item.card-listing` elements
- **Key Improvement**: Coordinates embedded directly in Google Maps links
- **Performance**: ~10x faster, no deep crawling needed for coordinates
- **Data Quality**: Rich metadata, 95%+ coordinate coverage, decimal ratings
- **Technology**: Modern selectors, rich data attributes, JSON-LD structured data

## Comprehensive Target Data Structure

### Core Venue Information
```typescript
interface Restaurant {
  // Basic identification
  id: string;                    // data-id="233153"
  name: string;                  // "Casa Del Vegano"
  slug: string;                  // "casa-del-vegano-dallas-233153"
  url: string;                   // Full HappyCow URL
  
  // Enhanced categorization
  category: {
    primary: 'vegan' | 'vegetarian' | 'veg-options';  // data-type
    icon: string;                // Category SVG icon URL
    label: string;               // "Vegan Restaurant"
  };
  
  // Comprehensive location data
  location: {
    // Address components
    streetAddress: string;       // "333 W Jefferson Blvd"
    city: string;               // "Dallas"
    state: string;              // "Texas"
    zipCode?: string;
    country: string;            // "USA"
    
    // Precise coordinates (from Google Maps links!)
    coordinates: {
      lat: number;              // 32.74339
      lng: number;              // -96.826994
    };
    
    // Maps integration
    googleMapsUrl: string;      // Direct Google Maps link
    neighborhood?: string;
    district?: string;
  };
  
  // Enhanced rating system
  rating: {
    score: number;              // 4.5 (decimal rating)
    reviewCount: number;        // 81
    hasTopRatedBadge: boolean;  // Special star icon
    ratingBreakdown?: {
      food?: number;
      service?: number;
      atmosphere?: number;
      value?: number;
    };
  };
  
  // Detailed cuisine and service information
  cuisine: {
    cuisineTags: string[];      // ["Mexican", "Beer/Wine", "Delivery"]
    serviceOptions: {
      delivery: boolean;
      takeout: boolean;
      dineIn: boolean;
      catering?: boolean;
    };
    dietaryFeatures: string[];  // ["Beer/Wine", "Gluten-Free Options"]
  };
  
  // Operating status and hours
  hours: {
    currentStatus: 'open_now' | 'closing_soon' | 'closed';
    statusText: string;         // "Open Now", "Closing Soon"
    statusColor: 'green' | 'red' | 'yellow';
    weeklyHours?: WeeklyHours;  // Detailed hours (from detail pages)
  };
  
  // Pricing information
  pricing: {
    priceRange: 1 | 2 | 3 | 4;  // Number of $ symbols
    priceRangeText: string;     // "$", "$$", "$$$", "$$$$"
    averageEntreePrice?: number;
    priceRangeEstimate?: {
      min: number;
      max: number;
    };
  };
  
  // Contact information
  contact: {
    phoneNumber?: string;       // "+1-972-685-3003"
    phoneFormatted?: string;    // "(972) 685-3003"
    website?: string;
    socialMedia?: {
      facebook?: string;
      instagram?: string;
      twitter?: string;
    };
    onlineOrderingUrl?: string;
    reservationUrl?: string;
  };
  
  // Visual content
  media: {
    primaryImage: {
      url: string;              // High-res image URL
      thumbnailUrl: string;     // Optimized thumbnail
      altText: string;          // "Image of Casa Del Vegano"
      placeholderData?: string; // Base64 placeholder
    };
    additionalImages?: ImageData[];
    menuImages?: ImageData[];
  };
  
  // Venue metadata and status
  metadata: {
    isTopRated: boolean;        // data-top="1"
    isNew: boolean;             // data-new="1"
    isPartner: boolean;         // data-partner="1"
    operationalStatus: 'open' | 'closing_soon' | 'closed' | 'temporarily_closed';
    specialNotes?: string;      // "Temporarily closed February 2025"
    ownerUpdates?: string;      // "please send updates to HappyCow"
  };
  
  // Accessibility and features
  features: {
    wheelchairAccessible?: boolean;
    hasParking?: boolean;
    parkingType?: 'free' | 'paid' | 'street' | 'valet';
    hasWifi?: boolean;
    acceptsReservations?: boolean;
    hasOutdoorSeating?: boolean;
    petFriendly?: boolean;
    paymentMethods?: string[];
  };
  
  // SEO and structured data
  seo: {
    schemaOrgData: {
      "@type": string;          // "Restaurant" | "FoodEstablishment"
      position: number;         // Position in search results
    };
    canonicalUrl: string;
    lastUpdated?: Date;
  };
  
  // Community and engagement
  community: {
    userPhotoCount?: number;
    isVerifiedBusiness?: boolean;
    claimedByOwner?: boolean;
    responseRate?: string;
  };
  
  // Scraping metadata
  scrapingInfo: {
    scrapedAt: Date;
    source: string;             // "happycow_listing" | "happycow_detail"
    version: string;            // Scraper version
    dataCompleteness: number;   // 0-1 score of data completeness
  };
}
```

## Enhanced Extraction Strategy

### Level 1: Listing Page Extraction (High Priority) 🔒
**Target**: All venues from city listing pages
**Selectors**: `div.venue-list-item.card-listing`

```typescript
const LISTING_SELECTORS = {
  // Core identification
  venueCard: 'div.venue-list-item.card-listing',
  venueId: '[data-id]',
  venueType: '[data-type]',
  venueLink: 'a.venue-item-link',
  
  // Metadata attributes
  isTopRated: '[data-top="1"]',
  isNew: '[data-new="1"]',
  isPartner: '[data-partner="1"]',
  
  // Basic information
  venueName: 'h4[data-analytics="listing-card-title"]',
  venueImage: 'img.card-listing-image',
  venueDescription: 'p.text-gray-800.text-base.font-normal.mt-2.line-clamp-3',
  
  // Rating and reviews
  ratingScore: 'div.mr-1', // Numeric rating
  reviewCount: 'div:contains("(")', // Review count in parentheses
  topRatedBadge: 'div[title="Top Rated Restaurant"]',
  
  // Category and cuisine
  categoryLabel: 'div.category-label',
  categoryIcon: 'img.category-label-img',
  cuisineTags: 'div.line-clamp-2.text-sm.mt-0\\.5',
  
  // Operating status
  hoursStatus: 'div.venue-hours-text',
  hoursStatusColor: 'div.venue-hours-text.text-green-500, div.venue-hours-text.text-red-500, div.venue-hours-text.text-yellow-500',
  
  // Pricing
  priceRange: 'span.price-range svg.price-range-item',
  
  // Contact information
  phoneNumber: 'a[href^="tel:"]',
  
  // Location and coordinates
  googleMapsLink: 'a[href*="google.com/maps"]',
  addressText: 'a[href*="google.com/maps"]', // Address in link text
  
  // Special notes
  specialNotes: 'p.venue-item-note',
  
  // JSON-LD structured data
  structuredData: 'script[type="application/ld+json"]'
};
```

### Level 2: Detail Page Extraction (Medium Priority) ⚠️
**Target**: Individual venue pages for complete data
**Trigger**: High-value venues or missing critical data

```typescript
const DETAIL_SELECTORS = {
  // Complete operating hours
  weeklyHours: '.hours-table, .operating-hours',
  holidayHours: '.holiday-hours, .special-hours',
  
  // Contact and digital presence
  website: 'a[href*="http"]:not([href*="happycow"])',
  socialLinks: 'a[href*="facebook"], a[href*="instagram"], a[href*="twitter"]',
  onlineOrdering: 'a[href*="order"], a[href*="delivery"]',
  reservations: 'a[href*="reservation"], a[href*="booking"]',
  
  // Enhanced media
  imageGallery: '.venue-images img, .photo-gallery img',
  menuImages: '.menu-images img, .menu-photos img',
  
  // Detailed features
  amenities: '.amenities, .features',
  accessibility: '.accessibility-info',
  parking: '.parking-info',
  
  // Owner information
  ownerInfo: '.owner-info, .business-info',
  ownerResponses: '.owner-response',
  
  // Menu information
  menuItems: '.menu-item, .dish-item',
  menuPrices: '.price, .menu-price',
  
  // User content
  userPhotos: '.user-photos img',
  userReviews: '.review, .user-review'
};
```

### Level 3: Enhanced Data Processing 💡

```typescript
const DATA_PROCESSORS = {
  // Coordinate extraction from Google Maps URLs
  extractCoordinates: (googleMapsUrl: string) => {
    const match = googleMapsUrl.match(/q=(-?\d+\.?\d*),(-?\d+\.?\d*)/);
    return match ? { lat: parseFloat(match[1]), lng: parseFloat(match[2]) } : null;
  },
  
  // Price range calculation
  calculatePriceRange: (priceSymbols: Element[]) => {
    const yellowSymbols = priceSymbols.filter(el => 
      el.classList.contains('text-yellow-500')
    ).length;
    return yellowSymbols;
  },
  
  // Status determination
  determineStatus: (statusElement: Element) => {
    if (statusElement.classList.contains('text-green-500')) return 'open_now';
    if (statusElement.classList.contains('text-red-500')) return 'closed';
    if (statusElement.classList.contains('text-yellow-500')) return 'closing_soon';
    return 'unknown';
  },
  
  // Cuisine tag parsing
  parseCuisineTags: (cuisineText: string) => {
    return cuisineText.split(',').map(tag => tag.trim());
  },
  
  // Image optimization
  optimizeImageUrl: (imageUrl: string, size: 'thumbnail' | 'medium' | 'large') => {
    const sizeMap = { thumbnail: '150', medium: '500', large: '1024' };
    return imageUrl.replace(/\/\d+\//, `/${sizeMap[size]}/`);
  }
};
```

## Implementation Phases

### Phase 1: Enhanced Core Scraper (2-3 days) 🔒
**Deliverables:**
- Complete listing page scraper with all Level 1 data
- Coordinate extraction from Google Maps links
- Enhanced data validation and cleaning
- Comprehensive error handling

**Technical Tasks:**
- Implement all listing page selectors
- Add coordinate extraction logic
- Build data validation pipeline
- Create comprehensive test suite
- Add rate limiting and respectful crawling

### Phase 2: Multi-City Scaling (2-3 days) 🔒
**Deliverables:**
- Automated city discovery and URL generation
- Pagination handling for large cities
- Database integration with full schema
- Progress tracking and resumption

**Target Cities (Priority Order):**
1. **Major US Cities**: NYC, LA, Chicago, SF, Austin, Portland, Seattle
2. **International**: London, Berlin, Toronto, Sydney, Tokyo
3. **Secondary US**: Denver, Atlanta, Miami, Boston, DC
4. **Comprehensive**: All cities with 10+ venues

### Phase 3: Detail Page Enhancement (3-4 days) ⚠️
**Deliverables:**
- Selective detail page scraping
- Complete operating hours extraction
- Social media and website discovery
- Enhanced image collection

**Smart Targeting:**
- Prioritize high-rated venues (4.0+ stars)
- Focus on venues with missing critical data
- Target popular destinations first
- Skip venues with complete listing data

### Phase 4: Advanced Features (2-3 days) 💡
**Deliverables:**
- Real-time status monitoring
- Change detection and updates
- Data quality scoring
- Analytics and insights

**Advanced Capabilities:**
- Detect venue closures and reopenings
- Monitor price and menu changes
- Track new venue additions
- Generate city-level statistics

### Phase 5: Production Integration (2-3 days) 🔒
**Deliverables:**
- Production database schema
- API integration
- Monitoring and alerting
- Documentation and maintenance guides

## Enhanced Technology Stack

### Core Technologies
- **Runtime**: Node.js 18+ with TypeScript
- **HTTP Client**: Axios with retry logic
- **HTML Parsing**: Cheerio for jQuery-like selectors
- **Data Validation**: Zod for schema validation
- **Database**: PostgreSQL with Prisma ORM
- **Queue System**: Bull/BullMQ for job processing
- **Monitoring**: Winston logging + Sentry error tracking

### Additional Tools
- **Image Processing**: Sharp for image optimization
- **Geocoding**: Google Maps API for address validation
- **Rate Limiting**: Bottleneck for request throttling
- **Caching**: Redis for response caching
- **Testing**: Jest with comprehensive test coverage

## Data Quality & Validation

### Validation Rules
```typescript
const VALIDATION_RULES = {
  coordinates: {
    lat: { min: -90, max: 90 },
    lng: { min: -180, max: 180 }
  },
  rating: {
    score: { min: 0, max: 5 },
    reviewCount: { min: 0 }
  },
  pricing: {
    priceRange: { min: 1, max: 4 }
  },
  contact: {
    phoneNumber: /^\+?[\d\s\-\(\)]+$/,
    email: /^[^\s@]+@[^\s@]+\.[^\s@]+$/
  }
};
```

### Data Completeness Scoring
```typescript
const calculateCompletenessScore = (restaurant: Restaurant): number => {
  const fields = {
    essential: ['name', 'location.coordinates', 'category.primary'], // Weight: 40%
    important: ['rating.score', 'contact.phoneNumber', 'hours.currentStatus'], // Weight: 35%
    nice_to_have: ['media.primaryImage', 'pricing.priceRange', 'cuisine.cuisineTags'] // Weight: 25%
  };
  
  // Calculate weighted score based on field presence and quality
  return calculateWeightedScore(restaurant, fields);
};
```

## Enhanced Rate Limiting & Ethics

### Respectful Crawling
```typescript
const CRAWLING_CONFIG = {
  requestDelay: 3000, // 3 seconds between requests
  maxConcurrency: 1,  // Single-threaded for politeness
  maxRetries: 3,
  timeout: 30000,
  
  headers: {
    'User-Agent': 'VeganVoyager Bot 1.0 (contact@veganvoyager.com)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
  }
};
```

### Error Handling & Recovery
```typescript
const ERROR_STRATEGIES = {
  networkError: 'retry_with_backoff',
  parseError: 'log_and_continue',
  validationError: 'fix_and_retry',
  rateLimit: 'exponential_backoff',
  captcha: 'manual_intervention'
};
```

## Expected Results & Timeline

### Data Volume Projections
- **Total Venues**: 15,000-20,000 globally
- **US Major Cities**: 8,000-10,000 venues
- **International**: 5,000-7,000 venues
- **Coordinate Coverage**: 95%+ (vs 60% with old method)
- **Complete Data**: 85%+ venues with full information

### Timeline Estimates
- **Phase 1 (Core)**: 2-3 days
- **Phase 2 (Scaling)**: 2-3 days  
- **Phase 3 (Enhancement)**: 3-4 days
- **Phase 4 (Advanced)**: 2-3 days
- **Phase 5 (Production)**: 2-3 days
- **Total**: 11-16 days

### Performance Metrics
- **Scraping Speed**: 1,200 venues/hour (vs 120 with old method)
- **Data Quality**: 95% accuracy rate
- **Coverage**: 98% of target venues successfully scraped
- **Maintenance**: Monthly updates to catch new venues

## Risk Mitigation

### Technical Risks
- **Site Changes**: Comprehensive selector testing and fallbacks
- **Rate Limiting**: Conservative delays and monitoring
- **Data Quality**: Multi-layer validation and manual spot checks
- **Scale Issues**: Incremental deployment and monitoring

### Legal & Ethical
- **Terms of Service**: Regular review and compliance
- **Attribution**: Proper crediting of HappyCow as data source
- **Usage Rights**: Clear guidelines for data usage
- **Privacy**: No personal data collection

## Success Metrics

### Quantitative Goals
- ✅ 95%+ coordinate coverage (vs 60% baseline)
- ✅ 10x performance improvement
- ✅ 15,000+ venues scraped successfully
- ✅ 85%+ data completeness score
- ✅ <1% error rate

### Qualitative Goals
- ✅ Rich, actionable venue data for users
- ✅ Real-time operating status
- ✅ Comprehensive search and filtering
- ✅ Seamless user experience
- ✅ Competitive advantage in vegan travel space

This enhanced plan positions VeganVoyager to build the most comprehensive vegan restaurant database available, with rich metadata and real-time information that goes far beyond basic directory listings. 