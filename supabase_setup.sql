-- HappyCow Scraper Database Setup for n8n Cloud
-- Run this in your Supabase SQL Editor

-- 1. Create restaurants table
CREATE TABLE IF NOT EXISTS restaurants (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    venue_id TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('vegan', 'vegetarian', 'veg-options', 'veg-friendly')),
    rating DECIMAL(2,1),
    review_count INTEGER DEFAULT 0,
    address TEXT,
    latitude DECIMAL(10,8),
    longitude DECIMAL(11,8),
    phone TEXT,
    website TEXT,
    cuisine_tags TEXT[],
    price_range TEXT CHECK (price_range IN ('$', '$$', '$$$', '$$$$')),
    features TEXT[],
    city_path TEXT NOT NULL,
    city_name TEXT NOT NULL,
    state_name TEXT NOT NULL,
    country_code TEXT NOT NULL DEFAULT 'US',
    scraped_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    page_number INTEGER DEFAULT 1,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 2. Create city queue table (replaces CSV file for cloud)
CREATE TABLE IF NOT EXISTS city_queue (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    state TEXT NOT NULL,
    city TEXT NOT NULL,
    entries INTEGER NOT NULL,
    full_path TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    trigger_status TEXT NOT NULL DEFAULT 'pending' 
        CHECK (trigger_status IN ('pending', 'running', 'completed', 'error', 'skip')),
    last_scraped TIMESTAMP WITH TIME ZONE,
    scrape_priority TEXT NOT NULL DEFAULT 'medium' 
        CHECK (scrape_priority IN ('high', 'medium', 'low')),
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Create scraping logs table
CREATE TABLE IF NOT EXISTS scraping_logs (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    city_path TEXT NOT NULL,
    city_name TEXT NOT NULL,
    state_name TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('started', 'completed', 'error')),
    restaurants_found INTEGER DEFAULT 0,
    pages_scraped INTEGER DEFAULT 0,
    error_message TEXT,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    workflow_id TEXT, -- n8n workflow execution ID
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_restaurants_city_path ON restaurants(city_path);
CREATE INDEX IF NOT EXISTS idx_restaurants_venue_id ON restaurants(venue_id);
CREATE INDEX IF NOT EXISTS idx_restaurants_type ON restaurants(type);
CREATE INDEX IF NOT EXISTS idx_restaurants_rating ON restaurants(rating DESC);
CREATE INDEX IF NOT EXISTS idx_restaurants_location ON restaurants(latitude, longitude);
CREATE INDEX IF NOT EXISTS idx_restaurants_scraped_at ON restaurants(scraped_at DESC);

CREATE INDEX IF NOT EXISTS idx_city_queue_status ON city_queue(trigger_status);
CREATE INDEX IF NOT EXISTS idx_city_queue_priority ON city_queue(scrape_priority);
CREATE INDEX IF NOT EXISTS idx_city_queue_entries ON city_queue(entries DESC);
CREATE INDEX IF NOT EXISTS idx_city_queue_last_scraped ON city_queue(last_scraped);

CREATE INDEX IF NOT EXISTS idx_scraping_logs_status ON scraping_logs(status);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_started_at ON scraping_logs(started_at DESC);
CREATE INDEX IF NOT EXISTS idx_scraping_logs_city_path ON scraping_logs(city_path);

-- 5. Create RLS policies (Row Level Security)
ALTER TABLE restaurants ENABLE ROW LEVEL SECURITY;
ALTER TABLE city_queue ENABLE ROW LEVEL SECURITY;
ALTER TABLE scraping_logs ENABLE ROW LEVEL SECURITY;

-- Allow service role to do everything (for n8n)
CREATE POLICY "Service role can manage restaurants" ON restaurants
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage city_queue" ON city_queue
    FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Service role can manage scraping_logs" ON scraping_logs
    FOR ALL USING (auth.role() = 'service_role');

-- 6. Create functions for common operations

-- Function to get next city to scrape
CREATE OR REPLACE FUNCTION get_next_city_to_scrape()
RETURNS TABLE (
    id UUID,
    state TEXT,
    city TEXT,
    entries INTEGER,
    full_path TEXT,
    url TEXT,
    scrape_priority TEXT
) 
LANGUAGE sql
AS $$
    SELECT 
        cq.id,
        cq.state,
        cq.city,
        cq.entries,
        cq.full_path,
        cq.url,
        cq.scrape_priority
    FROM city_queue cq
    WHERE cq.trigger_status = 'pending'
        AND (cq.last_scraped IS NULL OR cq.last_scraped < NOW() - INTERVAL '24 hours')
    ORDER BY 
        CASE cq.scrape_priority 
            WHEN 'high' THEN 1 
            WHEN 'medium' THEN 2 
            WHEN 'low' THEN 3 
        END,
        cq.entries DESC,
        cq.created_at ASC
    LIMIT 1;
$$;

-- Function to update city status
CREATE OR REPLACE FUNCTION update_city_status(
    city_id UUID,
    new_status TEXT,
    error_msg TEXT DEFAULT NULL
)
RETURNS VOID
LANGUAGE sql
AS $$
    UPDATE city_queue 
    SET 
        trigger_status = new_status,
        error_message = COALESCE(error_msg, error_message),
        retry_count = CASE 
            WHEN new_status = 'error' THEN retry_count + 1 
            ELSE retry_count 
        END,
        last_scraped = CASE 
            WHEN new_status = 'completed' THEN NOW() 
            ELSE last_scraped 
        END,
        updated_at = NOW()
    WHERE id = city_id;
$$;

-- Function to log scraping activity
CREATE OR REPLACE FUNCTION log_scraping_activity(
    city_path_param TEXT,
    city_name_param TEXT,
    state_name_param TEXT,
    status_param TEXT,
    restaurants_found_param INTEGER DEFAULT 0,
    pages_scraped_param INTEGER DEFAULT 0,
    error_message_param TEXT DEFAULT NULL,
    duration_seconds_param INTEGER DEFAULT NULL,
    workflow_id_param TEXT DEFAULT NULL
)
RETURNS UUID
LANGUAGE sql
AS $$
    INSERT INTO scraping_logs (
        city_path,
        city_name,
        state_name,
        status,
        restaurants_found,
        pages_scraped,
        error_message,
        completed_at,
        duration_seconds,
        workflow_id
    )
    VALUES (
        city_path_param,
        city_name_param,
        state_name_param,
        status_param,
        restaurants_found_param,
        pages_scraped_param,
        error_message_param,
        CASE WHEN status_param IN ('completed', 'error') THEN NOW() ELSE NULL END,
        duration_seconds_param,
        workflow_id_param
    )
    RETURNING id;
$$;

-- 7. Create view for dashboard/monitoring
CREATE OR REPLACE VIEW scraping_dashboard AS
SELECT 
    -- Queue status
    (SELECT COUNT(*) FROM city_queue WHERE trigger_status = 'pending') as pending_cities,
    (SELECT COUNT(*) FROM city_queue WHERE trigger_status = 'running') as running_cities,
    (SELECT COUNT(*) FROM city_queue WHERE trigger_status = 'completed') as completed_cities,
    (SELECT COUNT(*) FROM city_queue WHERE trigger_status = 'error') as error_cities,
    
    -- Restaurant stats
    (SELECT COUNT(*) FROM restaurants) as total_restaurants,
    (SELECT COUNT(*) FROM restaurants WHERE type = 'vegan') as vegan_restaurants,
    (SELECT COUNT(*) FROM restaurants WHERE type = 'vegetarian') as vegetarian_restaurants,
    (SELECT COUNT(*) FROM restaurants WHERE type IN ('veg-options', 'veg-friendly')) as veg_friendly_restaurants,
    
    -- Recent activity
    (SELECT COUNT(*) FROM scraping_logs WHERE started_at > NOW() - INTERVAL '24 hours') as scrapes_last_24h,
    (SELECT COUNT(*) FROM scraping_logs WHERE status = 'error' AND started_at > NOW() - INTERVAL '24 hours') as errors_last_24h,
    (SELECT AVG(duration_seconds) FROM scraping_logs WHERE status = 'completed' AND started_at > NOW() - INTERVAL '24 hours') as avg_duration_seconds_24h,
    
    -- Performance stats
    (SELECT AVG(restaurants_found) FROM scraping_logs WHERE status = 'completed') as avg_restaurants_per_city,
    (SELECT MAX(started_at) FROM scraping_logs) as last_scrape_time;

-- 8. Insert sample data to test (you can remove this after testing)
INSERT INTO city_queue (state, city, entries, full_path, url, scrape_priority) VALUES
('Texas', 'Dallas', 193, 'north_america/usa/texas/dallas', 'https://www.happycow.net/north_america/usa/texas/dallas/', 'high'),
('California', 'Los Angeles', 686, 'north_america/usa/california/los_angeles', 'https://www.happycow.net/north_america/usa/california/los_angeles/', 'high'),
('New York', 'New York City', 1207, 'north_america/usa/new_york/new_york', 'https://www.happycow.net/north_america/usa/new_york/new_york/', 'high')
ON CONFLICT (full_path) DO NOTHING;

-- 9. Grant permissions to service role (n8n will use this)
GRANT ALL ON restaurants TO service_role;
GRANT ALL ON city_queue TO service_role;
GRANT ALL ON scraping_logs TO service_role;
GRANT EXECUTE ON FUNCTION get_next_city_to_scrape() TO service_role;
GRANT EXECUTE ON FUNCTION update_city_status(UUID, TEXT, TEXT) TO service_role;
GRANT EXECUTE ON FUNCTION log_scraping_activity(TEXT, TEXT, TEXT, TEXT, INTEGER, INTEGER, TEXT, INTEGER, TEXT) TO service_role;
GRANT SELECT ON scraping_dashboard TO service_role; 