// HappyCow Scraper Usage Examples and Utilities
import { HappyCowScraper, type ScrapingResult, type Venue } from './happycow-scraper';
import { writeFileSync, existsSync, mkdirSync } from 'fs';
import { join } from 'path';

// 🎯 Usage Examples

/**
 * Basic usage - scrape a single city page
 */
export async function scrapeSingleCity(cityUrl: string): Promise<ScrapingResult> {
  const scraper = new HappyCowScraper({
    rateLimitDelay: 3000, // 3 seconds between requests
  });

  try {
    const result = await scraper.scrapeCityListings(cityUrl);
    console.log(`Found ${result.totalVenues} venues in ${result.city}, ${result.state}`);
    return result;
  } catch (error) {
    console.error('Scraping failed:', error);
    throw error;
  }
}

/**
 * Advanced usage - scrape all pages for a city
 */
export async function scrapeAllPagesForCity(cityUrl: string): Promise<ScrapingResult> {
  const scraper = new HappyCowScraper({
    rateLimitDelay: 2000, // 2 seconds for multiple pages
  });

  try {
    console.log(`Starting comprehensive scrape of: ${cityUrl}`);
    const allResults = await scraper.scrapeAllPages(cityUrl);
    
    console.log(`Scraped ${allResults.length} pages total`);
    
    const combined = HappyCowScraper.combineResults(allResults);
    console.log(`Total venues found: ${combined.totalVenues}`);
    
    return combined;
  } catch (error) {
    console.error('Multi-page scraping failed:', error);
    throw error;
  }
}

/**
 * Scrape multiple cities
 */
export async function scrapeMultipleCities(cityUrls: string[]): Promise<ScrapingResult[]> {
  const scraper = new HappyCowScraper({
    rateLimitDelay: 4000, // More conservative for multiple cities
  });

  const results: ScrapingResult[] = [];

  for (const [index, cityUrl] of cityUrls.entries()) {
    try {
      console.log(`[${index + 1}/${cityUrls.length}] Scraping: ${cityUrl}`);
      const result = await scraper.scrapeCityListings(cityUrl);
      results.push(result);
      
      // Extra delay between cities
      if (index < cityUrls.length - 1) {
        console.log('Waiting 5 seconds before next city...');
        await new Promise(resolve => setTimeout(resolve, 5000));
      }
    } catch (error) {
      console.error(`Failed to scrape ${cityUrl}:`, error);
    }
  }

  return results;
}

// 🎯 Output Utilities

/**
 * Save results to JSON file
 */
export function saveToJSON(result: ScrapingResult, outputPath: string): void {
  const dir = join(outputPath, '../');
  if (!existsSync(dir)) {
    mkdirSync(dir, { recursive: true });
  }

  const data = {
    ...result,
    // Add metadata
    generatedBy: 'HappyCow Scraper for VeganVoyager',
    generatedAt: new Date().toISOString(),
    version: '1.0.0',
  };

  writeFileSync(outputPath, JSON.stringify(data, null, 2), 'utf-8');
  console.log(`Results saved to: ${outputPath}`);
}

/**
 * Convert to CSV format for analysis
 */
export function convertToCSV(venues: Venue[]): string {
  const headers = [
    'id', 'name', 'type', 'rating', 'reviewCount', 'priceRange',
    'lat', 'lng', 'address', 'phone', 'description', 'features',
    'isOpen', 'isTopRated', 'happyCowUrl'
  ];

  const rows = venues.map(venue => [
    venue.id,
    `"${venue.name.replace(/"/g, '""')}"`, // Escape quotes
    venue.type,
    venue.rating || '',
    venue.reviewCount || '',
    venue.priceRange || '',
    venue.coordinates?.lat || '',
    venue.coordinates?.lng || '',
    `"${(venue.address || '').replace(/"/g, '""')}"`,
    venue.phone || '',
    `"${(venue.description || '').replace(/"/g, '""')}"`,
    `"${(venue.features || []).join(', ')}"`,
    venue.isOpen || false,
    venue.isTopRated || false,
    venue.happyCowUrl
  ]);

  return [headers.join(','), ...rows.map(row => row.join(','))].join('\n');
}

/**
 * Generate summary statistics
 */
export function generateSummary(result: ScrapingResult): {
  totalVenues: number;
  byType: Record<string, number>;
  byPriceRange: Record<string, number>;
  avgRating: number;
  topRatedCount: number;
  withCoordinates: number;
  withPhone: number;
  openNow: number;
} {
  const venues = result.venues;

  return {
    totalVenues: venues.length,
    byType: venues.reduce((acc, v) => {
      acc[v.type] = (acc[v.type] || 0) + 1;
      return acc;
    }, {} as Record<string, number>),
    byPriceRange: venues.reduce((acc, v) => {
      const range = v.priceRange ? `${'$'.repeat(v.priceRange)}` : 'Unknown';
      acc[range] = (acc[range] || 0) + 1;
      return acc;
    }, {} as Record<string, number>),
    avgRating: venues.filter(v => v.rating).reduce((sum, v) => sum + (v.rating || 0), 0) / venues.filter(v => v.rating).length,
    topRatedCount: venues.filter(v => v.isTopRated).length,
    withCoordinates: venues.filter(v => v.coordinates).length,
    withPhone: venues.filter(v => v.phone).length,
    openNow: venues.filter(v => v.isOpen).length,
  };
}

// 🎯 Popular City URLs for testing
export const POPULAR_CITIES = {
  // US Major Cities
  'New York': 'https://www.happycow.net/north_america/usa/new_york/new_york/',
  'Los Angeles': 'https://www.happycow.net/north_america/usa/california/los_angeles/',
  'San Francisco': 'https://www.happycow.net/north_america/usa/california/san_francisco/',
  'Dallas': 'https://www.happycow.net/north_america/usa/texas/dallas/',
  'Chicago': 'https://www.happycow.net/north_america/usa/illinois/chicago/',
  'Austin': 'https://www.happycow.net/north_america/usa/texas/austin/',
  'Portland': 'https://www.happycow.net/north_america/usa/oregon/portland/',
  'Seattle': 'https://www.happycow.net/north_america/usa/washington/seattle/',
  
  // International
  'London': 'https://www.happycow.net/europe/united_kingdom/england/london/',
  'Berlin': 'https://www.happycow.net/europe/germany/berlin/',
  'Tokyo': 'https://www.happycow.net/asia/japan/tokyo/',
  'Tel Aviv': 'https://www.happycow.net/middle_east/israel/tel_aviv/',
};

// 🎯 Example usage functions
export async function quickTest() {
  console.log('🌱 Quick HappyCow Scraper Test');
  
  try {
    const result = await scrapeSingleCity(POPULAR_CITIES.Dallas);
    const summary = generateSummary(result);
    
    console.log('\n📊 Summary:');
    console.log(`Total venues: ${summary.totalVenues}`);
    console.log(`By type:`, summary.byType);
    console.log(`Average rating: ${summary.avgRating.toFixed(1)}`);
    console.log(`Top rated: ${summary.topRatedCount}`);
    console.log(`With coordinates: ${summary.withCoordinates}`);
    
    // Save sample results
    saveToJSON(result, './data/dallas-sample.json');
    
  } catch (error) {
    console.error('Test failed:', error);
  }
}

export async function comprehensiveTest() {
  console.log('🌱 Comprehensive HappyCow Scraper Test');
  
  const testCities = [
    POPULAR_CITIES.Dallas,
    POPULAR_CITIES.Austin,
  ];
  
  try {
    const results = await scrapeMultipleCities(testCities);
    
    for (const result of results) {
      const summary = generateSummary(result);
      console.log(`\n📊 ${result.city}, ${result.state}:`);
      console.log(`- Total venues: ${summary.totalVenues}`);
      console.log(`- Vegan: ${summary.byType.vegan || 0}`);
      console.log(`- Vegetarian: ${summary.byType.vegetarian || 0}`);
      console.log(`- Veg-options: ${summary.byType['veg-options'] || 0}`);
      
      // Save individual city results
      const filename = `./data/${result.city.toLowerCase()}-${result.state.toLowerCase()}.json`;
      saveToJSON(result, filename);
    }
    
  } catch (error) {
    console.error('Comprehensive test failed:', error);
  }
} 