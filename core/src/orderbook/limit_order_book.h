#pragma once

#include <unordered_map>
#include <map>
#include <string>
#include <memory>
#include <cstdint>
#include <vector>

namespace microstructure {

struct Order {
    std::string order_id;
    double price;
    double quantity;
    bool is_buy;
    int64_t timestamp_ns;
    
    // Comparison operators for efficient management
    bool operator==(const Order& other) const {
        return order_id == other.order_id;
    }
};

// Forward declarations
class PriceLevel;

using OrderPtr = std::shared_ptr<Order>;
using PriceLevelPtr = std::shared_ptr<PriceLevel>;

// Price level in the order book
class PriceLevel {
public:
    explicit PriceLevel(double price) : price_(price) {}
    
    void AddOrder(const OrderPtr& order);
    void RemoveOrder(const std::string& order_id);
    double GetTotalVolume() const;
    const std::vector<OrderPtr>& GetOrders() const;
    
private:
    double price_;
    std::vector<OrderPtr> orders_;
    double total_volume_ = 0.0;
};

// Main limit order book implementation
class LimitOrderBook {
public:
    LimitOrderBook(const std::string& symbol) : symbol_(symbol) {}
    
    // Core order book operations
    void AddOrder(const OrderPtr& order);
    void ModifyOrder(const std::string& order_id, double new_quantity);
    void CancelOrder(const std::string& order_id);
    
    // Order book queries
    double GetBestBid() const;
    double GetBestAsk() const;
    double GetMidPrice() const;
    double GetSpread() const;
    
    // Market impact estimation
    double EstimateMarketImpact(bool is_buy, double quantity) const;
    
    // Order book metrics
    double GetOrderImbalance(int levels = 5) const;
    std::vector<std::pair<double, double>> GetBidLevels(int count = 10) const;
    std::vector<std::pair<double, double>> GetAskLevels(int count = 10) const;
    
private:
    std::string symbol_;
    
    // Order lookup for O(1) access by ID
    std::unordered_map<std::string, OrderPtr> orders_;
    
    // Price level organization - using maps for price-time priority
    std::map<double, PriceLevelPtr, std::greater<double>> bids_; // Higher prices first
    std::map<double, PriceLevelPtr> asks_; // Lower prices first
    
    // Statistics for quick access
    double best_bid_ = 0.0;
    double best_ask_ = std::numeric_limits<double>::max();
    
    // Helper methods
    void UpdateBestPrices();
};

} // namespace microstructure 