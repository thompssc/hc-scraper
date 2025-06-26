/**
 * HappyCow Scraping Foundation for VeganVoyager
 * 
 * This file contains the core data structures, validation schemas, and utility
 * functions for scraping restaurant data from HappyCow's modern website structure.
 * 
 * Key Features:
 * - Comprehensive data extraction from listing pages
 * - Coordinate extraction from Google Maps links (no deep crawling needed)
 * - Rich metadata capture (ratings, status, features, etc.)
 * - Multi-level data validation with Zod schemas
 * - Respectful rate limiting and error handling
 * 
 * @version 2.0.0
 * @updated 2024-12-19
 */

import { z } from 'zod';

// =============================================================================
// COMPREHENSIVE DATA SCHEMAS
// =============================================================================

/**
 * Enhanced Location Schema with full address breakdown and coordinates
 */
export const LocationSchema = z.object({
  // Address components
  streetAddress: z.string().min(1),
  city: z.string().min(1),
  state: z.string().min(1),
  zipCode: z.string().optional(),
  country: z.string().default('USA'),
  
  // Precise coordinates (extracted from Google Maps links)
  coordinates: z.object({
    lat: z.number().min(-90).max(90),
    lng: z.number().min(-180).max(180)
  }),
  
  // Maps integration
  googleMapsUrl: z.string().url(),
  neighborhood: z.string().optional(),
  district: z.string().optional()
});

/**
 * Enhanced Category Schema with visual indicators
 */
export const CategorySchema = z.object({
  primary: z.enum(['vegan', 'vegetarian', 'veg-options']),
  icon: z.string().url(),
  label: z.string()
});

/**
 * Comprehensive Rating Schema with breakdown support
 */
export const RatingSchema = z.object({
  score: z.number().min(0).max(5),
  reviewCount: z.number().min(0),
  hasTopRatedBadge: z.boolean(),
  ratingBreakdown: z.object({
    food: z.number().min(0).max(5).optional(),
    service: z.number().min(0).max(5).optional(),
    atmosphere: z.number().min(0).max(5).optional(),
    value: z.number().min(0).max(5).optional()
  }).optional()
});

/**
 * Detailed Cuisine and Service Information Schema
 */
export const CuisineSchema = z.object({
  cuisineTags: z.array(z.string()),
  serviceOptions: z.object({
    delivery: z.boolean(),
    takeout: z.boolean(),
    dineIn: z.boolean(),
    catering: z.boolean().optional()
  }),
  dietaryFeatures: z.array(z.string())
});

/**
 * Operating Hours and Status Schema
 */
export const HoursSchema = z.object({
  currentStatus: z.enum(['open_now', 'closing_soon', 'closed']),
  statusText: z.string(),
  statusColor: z.enum(['green', 'red', 'yellow']),
  weeklyHours: z.object({
    monday: z.string().optional(),
    tuesday: z.string().optional(),
    wednesday: z.string().optional(),
    thursday: z.string().optional(),
    friday: z.string().optional(),
    saturday: z.string().optional(),
    sunday: z.string().optional()
  }).optional()
});

/**
 * Pricing Information Schema
 */
export const PricingSchema = z.object({
  priceRange: z.number().min(1).max(4),
  priceRangeText: z.enum(['$', '$$', '$$$', '$$$$']),
  averageEntreePrice: z.number().positive().optional(),
  priceRangeEstimate: z.object({
    min: z.number().positive(),
    max: z.number().positive()
  }).optional()
});

/**
 * Contact Information Schema
 */
export const ContactSchema = z.object({
  phoneNumber: z.string().regex(/^\+?[\d\s\-\(\)]+$/).optional(),
  phoneFormatted: z.string().optional(),
  website: z.string().url().optional(),
  socialMedia: z.object({
    facebook: z.string().url().optional(),
    instagram: z.string().url().optional(),
    twitter: z.string().url().optional()
  }).optional(),
  onlineOrderingUrl: z.string().url().optional(),
  reservationUrl: z.string().url().optional()
});

/**
 * Media Content Schema
 */
export const MediaSchema = z.object({
  primaryImage: z.object({
    url: z.string().url(),
    thumbnailUrl: z.string().url(),
    altText: z.string(),
    placeholderData: z.string().optional()
  }),
  additionalImages: z.array(z.object({
    url: z.string().url(),
    altText: z.string(),
    caption: z.string().optional()
  })).optional(),
  menuImages: z.array(z.object({
    url: z.string().url(),
    altText: z.string(),
    menuSection: z.string().optional()
  })).optional()
});

/**
 * Venue Metadata and Status Schema
 */
export const MetadataSchema = z.object({
  isTopRated: z.boolean(),
  isNew: z.boolean(),
  isPartner: z.boolean(),
  operationalStatus: z.enum(['open', 'closing_soon', 'closed', 'temporarily_closed']),
  specialNotes: z.string().optional(),
  ownerUpdates: z.string().optional()
});

/**
 * Accessibility and Features Schema
 */
export const FeaturesSchema = z.object({
  wheelchairAccessible: z.boolean().optional(),
  hasParking: z.boolean().optional(),
  parkingType: z.enum(['free', 'paid', 'street', 'valet']).optional(),
  hasWifi: z.boolean().optional(),
  acceptsReservations: z.boolean().optional(),
  hasOutdoorSeating: z.boolean().optional(),
  petFriendly: z.boolean().optional(),
  paymentMethods: z.array(z.string()).optional()
});

/**
 * SEO and Structured Data Schema
 */
export const SEOSchema = z.object({
  schemaOrgData: z.object({
    '@type': z.string(),
    position: z.number().positive()
  }),
  canonicalUrl: z.string().url(),
  lastUpdated: z.date().optional()
});

/**
 * Community and Engagement Schema
 */
export const CommunitySchema = z.object({
  userPhotoCount: z.number().min(0).optional(),
  isVerifiedBusiness: z.boolean().optional(),
  claimedByOwner: z.boolean().optional(),
  responseRate: z.string().optional()
});

/**
 * Scraping Metadata Schema
 */
export const ScrapingInfoSchema = z.object({
  scrapedAt: z.date(),
  source: z.enum(['happycow_listing', 'happycow_detail']),
  version: z.string(),
  dataCompleteness: z.number().min(0).max(1)
});

/**
 * Complete Restaurant Schema combining all components
 */
export const RestaurantSchema = z.object({
  // Basic identification
  id: z.string(),
  name: z.string().min(1),
  slug: z.string(),
  url: z.string().url(),
  
  // Enhanced data components
  category: CategorySchema,
  location: LocationSchema,
  rating: RatingSchema,
  cuisine: CuisineSchema,
  hours: HoursSchema,
  pricing: PricingSchema,
  contact: ContactSchema,
  media: MediaSchema,
  metadata: MetadataSchema,
  features: FeaturesSchema,
  seo: SEOSchema,
  community: CommunitySchema,
  scrapingInfo: ScrapingInfoSchema
});

// =============================================================================
// TYPE DEFINITIONS
// =============================================================================

export type Restaurant = z.infer<typeof RestaurantSchema>;
export type Location = z.infer<typeof LocationSchema>;
export type Category = z.infer<typeof CategorySchema>;
export type Rating = z.infer<typeof RatingSchema>;
export type Cuisine = z.infer<typeof CuisineSchema>;
export type Hours = z.infer<typeof HoursSchema>;
export type Pricing = z.infer<typeof PricingSchema>;
export type Contact = z.infer<typeof ContactSchema>;
export type Media = z.infer<typeof MediaSchema>;
export type Metadata = z.infer<typeof MetadataSchema>;
export type Features = z.infer<typeof FeaturesSchema>;
export type SEO = z.infer<typeof SEOSchema>;
export type Community = z.infer<typeof CommunitySchema>;
export type ScrapingInfo = z.infer<typeof ScrapingInfoSchema>;

// =============================================================================
// ENHANCED SELECTOR CONFIGURATION
// =============================================================================

/**
 * Comprehensive CSS selectors for listing page extraction
 */
export const LISTING_SELECTORS = {
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
} as const;

/**
 * Detail page selectors for enhanced data extraction
 */
export const DETAIL_SELECTORS = {
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
} as const;

// =============================================================================
// ENHANCED DATA PROCESSING UTILITIES
// =============================================================================

/**
 * Extract coordinates from Google Maps URLs
 */
export const extractCoordinates = (googleMapsUrl: string): { lat: number; lng: number } | null => {
  const match = googleMapsUrl.match(/q=(-?\d+\.?\d*),(-?\d+\.?\d*)/);
  return match ? { lat: parseFloat(match[1]), lng: parseFloat(match[2]) } : null;
};

/**
 * Calculate price range from visual dollar sign elements
 */
export const calculatePriceRange = (priceElements: Element[]): number => {
  const yellowSymbols = priceElements.filter(el => 
    el.classList.contains('text-yellow-500')
  ).length;
  return Math.max(1, Math.min(4, yellowSymbols));
};

/**
 * Determine operational status from CSS classes
 */
export const determineStatus = (statusElement: Element): Hours['currentStatus'] => {
  if (statusElement.classList.contains('text-green-500')) return 'open_now';
  if (statusElement.classList.contains('text-red-500')) return 'closed';
  if (statusElement.classList.contains('text-yellow-500')) return 'closing_soon';
  return 'closed'; // Default fallback
};

/**
 * Parse cuisine tags from comma-separated text
 */
export const parseCuisineTags = (cuisineText: string): string[] => {
  return cuisineText.split(',')
    .map(tag => tag.trim())
    .filter(tag => tag.length > 0);
};

/**
 * Optimize image URLs for different sizes
 */
export const optimizeImageUrl = (
  imageUrl: string, 
  size: 'thumbnail' | 'medium' | 'large'
): string => {
  const sizeMap = { thumbnail: '150', medium: '500', large: '1024' };
  return imageUrl.replace(/\/\d+\//, `/${sizeMap[size]}/`);
};

/**
 * Extract phone number from tel: links
 */
export const extractPhoneNumber = (telLink: string): string => {
  return telLink.replace('tel:', '').trim();
};

/**
 * Parse review count from text like "(81)"
 */
export const parseReviewCount = (reviewText: string): number => {
  const match = reviewText.match(/\((\d+)\)/);
  return match ? parseInt(match[1], 10) : 0;
};

/**
 * Generate price range text from numeric value
 */
export const generatePriceRangeText = (priceRange: number): Pricing['priceRangeText'] => {
  const map = { 1: '$', 2: '$$', 3: '$$$', 4: '$$$$' } as const;
  return map[priceRange as keyof typeof map] || '$';
};

/**
 * Calculate data completeness score
 */
export const calculateCompletenessScore = (restaurant: Partial<Restaurant>): number => {
  const weights = {
    essential: 0.4, // name, coordinates, category
    important: 0.35, // rating, phone, status
    nice_to_have: 0.25 // image, price, cuisine
  };
  
  const essential = [
    restaurant.name,
    restaurant.location?.coordinates,
    restaurant.category?.primary
  ].filter(Boolean).length / 3;
  
  const important = [
    restaurant.rating?.score,
    restaurant.contact?.phoneNumber,
    restaurant.hours?.currentStatus
  ].filter(Boolean).length / 3;
  
  const niceToHave = [
    restaurant.media?.primaryImage,
    restaurant.pricing?.priceRange,
    restaurant.cuisine?.cuisineTags?.length
  ].filter(Boolean).length / 3;
  
  return (
    essential * weights.essential +
    important * weights.important +
    niceToHave * weights.nice_to_have
  );
};

// =============================================================================
// ERROR HANDLING CLASSES
// =============================================================================

/**
 * Base error class for HappyCow scraping operations
 */
export class HappyCowScrapingError extends Error {
  constructor(
    message: string,
    public code: string,
    public retryable: boolean = false,
    public statusCode?: number,
    public context?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'HappyCowScrapingError';
  }
}

/**
 * Network-related errors (timeouts, connection issues)
 */
export class NetworkError extends HappyCowScrapingError {
  constructor(message: string, statusCode?: number) {
    super(message, 'NETWORK_ERROR', true, statusCode);
    this.name = 'NetworkError';
  }
}

/**
 * HTML parsing and structure errors
 */
export class ParseError extends HappyCowScrapingError {
  constructor(message: string, context?: Record<string, unknown>) {
    super(message, 'PARSE_ERROR', false, undefined, context);
    this.name = 'ParseError';
  }
}

/**
 * Data validation errors
 */
export class ValidationError extends HappyCowScrapingError {
  constructor(message: string, validationErrors: unknown) {
    super(message, 'VALIDATION_ERROR', false, undefined, { validationErrors });
    this.name = 'ValidationError';
  }
}

/**
 * Rate limiting errors
 */
export class RateLimitError extends HappyCowScrapingError {
  constructor(message: string, retryAfter?: number) {
    super(message, 'RATE_LIMIT_ERROR', true, 429, { retryAfter });
    this.name = 'RateLimitError';
  }
}

// =============================================================================
// CONFIGURATION CONSTANTS
// =============================================================================

/**
 * Rate limiting and request configuration
 */
export const SCRAPING_CONFIG = {
  // Request timing
  requestDelay: 3000, // 3 seconds between requests
  maxConcurrency: 1,  // Single-threaded for politeness
  maxRetries: 3,
  timeout: 30000, // 30 seconds
  
  // Headers for respectful crawling
  headers: {
    'User-Agent': 'VeganVoyager Bot 2.0 (contact@veganvoyager.com)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1'
  },
  
  // Error handling
  retryDelays: [1000, 2000, 4000], // Exponential backoff
  maxErrorsPerCity: 10,
  
  // Data quality
  minDataCompleteness: 0.6, // 60% minimum completeness
  requireCoordinates: true,
  requireRating: false
} as const;

/**
 * Target cities with their HappyCow URLs (Priority Order)
 */
export const TARGET_CITIES = {
  // Tier 1: Major US vegan hubs
  'New York': 'https://www.happycow.net/north_america/usa/new_york/new_york/',
  'Los Angeles': 'https://www.happycow.net/north_america/usa/california/los_angeles/',
  'San Francisco': 'https://www.happycow.net/north_america/usa/california/san_francisco/',
  'Portland': 'https://www.happycow.net/north_america/usa/oregon/portland/',
  'Austin': 'https://www.happycow.net/north_america/usa/texas/austin/',
  'Seattle': 'https://www.happycow.net/north_america/usa/washington/seattle/',
  
  // Tier 2: Large US cities
  'Chicago': 'https://www.happycow.net/north_america/usa/illinois/chicago/',
  'Dallas': 'https://www.happycow.net/north_america/usa/texas/dallas/',
  'Denver': 'https://www.happycow.net/north_america/usa/colorado/denver/',
  'Atlanta': 'https://www.happycow.net/north_america/usa/georgia/atlanta/',
  'Miami': 'https://www.happycow.net/north_america/usa/florida/miami/',
  'Boston': 'https://www.happycow.net/north_america/usa/massachusetts/boston/',
  'Washington DC': 'https://www.happycow.net/north_america/usa/district_of_columbia/washington/',
  
  // Tier 3: International cities
  'London': 'https://www.happycow.net/europe/united_kingdom/england/london/',
  'Berlin': 'https://www.happycow.net/europe/germany/berlin/',
  'Toronto': 'https://www.happycow.net/north_america/canada/ontario/toronto/',
  'Amsterdam': 'https://www.happycow.net/europe/netherlands/amsterdam/',
  'Tokyo': 'https://www.happycow.net/asia/japan/tokyo/',
  'Sydney': 'https://www.happycow.net/oceania/australia/new_south_wales/sydney/',
  'Tel Aviv': 'https://www.happycow.net/middle_east/israel/tel_aviv/',
  'Bangkok': 'https://www.happycow.net/asia/thailand/bangkok/'
} as const;

/**
 * Error handling strategies
 */
export const ERROR_STRATEGIES = {
  networkError: 'retry_with_backoff',
  parseError: 'log_and_continue',
  validationError: 'fix_and_retry',
  rateLimit: 'exponential_backoff',
  captcha: 'manual_intervention'
} as const;

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Generate a unique slug from restaurant name and ID
 */
export const generateSlug = (name: string, id: string): string => {
  const cleanName = name
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .trim();
  
  return `${cleanName}-${id}`;
};

/**
 * Validate and clean phone number
 */
export const cleanPhoneNumber = (phone: string): string => {
  return phone.replace(/[^\d+\-\(\)\s]/g, '').trim();
};

/**
 * Extract city information from URL path
 */
export const extractCityInfo = (url: string): { city: string; state?: string; country: string } => {
  const pathParts = url.split('/').filter(Boolean);
  const country = pathParts[0] || 'unknown';
  const state = pathParts[1] || undefined;
  const city = pathParts[pathParts.length - 1] || 'unknown';
  
  return { city, state, country };
};

/**
 * Sleep utility for rate limiting
 */
export const sleep = (ms: number): Promise<void> => {
  return new Promise(resolve => setTimeout(resolve, ms));
};

/**
 * Retry function with exponential backoff
 */
export const retryWithBackoff = async <T>(
  fn: () => Promise<T>,
  maxRetries: number = 3,
  baseDelay: number = 1000
): Promise<T> => {
  for (let attempt = 1; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries) throw error;
      
      const delay = baseDelay * Math.pow(2, attempt - 1);
      await sleep(delay);
    }
  }
  
  throw new Error('Max retries exceeded');
};

// =============================================================================
// VALIDATION HELPERS
// =============================================================================

/**
 * Validate extracted restaurant data
 */
export const validateRestaurant = (data: unknown): Restaurant => {
  try {
    return RestaurantSchema.parse(data);
  } catch (error) {
    throw new ValidationError('Restaurant data validation failed', error);
  }
};

/**
 * Validate coordinates are within reasonable bounds
 */
export const validateCoordinates = (lat: number, lng: number): boolean => {
  return lat >= -90 && lat <= 90 && lng >= -180 && lng <= 180;
};

/**
 * Check if URL is a valid HappyCow venue URL
 */
export const isValidHappyCowUrl = (url: string): boolean => {
  return url.includes('happycow.net/reviews/') && url.length > 30;
};

// =============================================================================
// EXPORTS
// =============================================================================

export default {
  // Schemas
  RestaurantSchema,
  LocationSchema,
  CategorySchema,
  RatingSchema,
  CuisineSchema,
  HoursSchema,
  PricingSchema,
  ContactSchema,
  MediaSchema,
  MetadataSchema,
  FeaturesSchema,
  SEOSchema,
  CommunitySchema,
  ScrapingInfoSchema,
  
  // Selectors
  LISTING_SELECTORS,
  DETAIL_SELECTORS,
  
  // Utilities
  extractCoordinates,
  calculatePriceRange,
  determineStatus,
  parseCuisineTags,
  optimizeImageUrl,
  extractPhoneNumber,
  parseReviewCount,
  generatePriceRangeText,
  calculateCompletenessScore,
  
  // Error classes
  HappyCowScrapingError,
  NetworkError,
  ParseError,
  ValidationError,
  RateLimitError,
  
  // Configuration
  SCRAPING_CONFIG,
  TARGET_CITIES,
  ERROR_STRATEGIES,
  
  // Helpers
  generateSlug,
  cleanPhoneNumber,
  extractCityInfo,
  sleep,
  retryWithBackoff,
  validateRestaurant,
  validateCoordinates,
  isValidHappyCowUrl
}; 