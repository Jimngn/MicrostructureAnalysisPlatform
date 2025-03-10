#include "limit_order_book.h"
#include <algorithm>
#include <iostream>
#include <limits>

namespace microstructure {

void PriceLevel::AddOrder(const OrderPtr& order) {
    orders_.push_back(order);
    total_volume_ += order->quantity;
}

void PriceLevel::RemoveOrder(const std::string& order_id) {
    auto it = std::find_if(orders_.begin(), orders_.end(),
                          [&order_id](const OrderPtr& order) {
                              return order->order_id == order_id;
                          });
    
    if (it != orders_.end()) {
        total_volume_ -= (*it)->quantity;
        orders_.erase(it);
    }
}

double PriceLevel::GetTotalVolume() const {
    return total_volume_;
}

const std::vector<OrderPtr>& PriceLevel::GetOrders() const {
    return orders_;
}

void LimitOrderBook::AddOrder(const OrderPtr& order) {
    // Store the order in the lookup map
    orders_[order->order_id] = order;
    
    // Add to the appropriate side of the book
    if (order->is_buy) {
        auto it = bids_.find(order->price);
        if (it == bids_.end()) {
            auto level = std::make_shared<PriceLevel>(order->price);
            level->AddOrder(order);
            bids_[order->price] = level;
        } else {
            it->second->AddOrder(order);
        }
    } else {
        auto it = asks_.find(order->price);
        if (it == asks_.end()) {
            auto level = std::make_shared<PriceLevel>(order->price);
            level->AddOrder(order);
            asks_[order->price] = level;
        } else {
            it->second->AddOrder(order);
        }
    }
    
    UpdateBestPrices();
}

void LimitOrderBook::ModifyOrder(const std::string& order_id, double new_quantity) {
    auto it = orders_.find(order_id);
    if (it == orders_.end()) {
        return;
    }
    
    OrderPtr order = it->second;
    double delta = new_quantity - order->quantity;
    order->quantity = new_quantity;
    
    // Update the price level totals
    if (order->is_buy) {
        bids_[order->price]->AddOrder(order);
    } else {
        asks_[order->price]->AddOrder(order);
    }
}

void LimitOrderBook::CancelOrder(const std::string& order_id) {
    auto it = orders_.find(order_id);
    if (it == orders_.end()) {
        return;
    }
    
    OrderPtr order = it->second;
    
    // Remove from the appropriate side of the book
    if (order->is_buy) {
        auto level_it = bids_.find(order->price);
        if (level_it != bids_.end()) {
            level_it->second->RemoveOrder(order_id);
            
            // If level is empty, remove it
            if (level_it->second->GetTotalVolume() <= 0) {
                bids_.erase(level_it);
            }
        }
    } else {
        auto level_it = asks_.find(order->price);
        if (level_it != asks_.end()) {
            level_it->second->RemoveOrder(order_id);
            
            // If level is empty, remove it
            if (level_it->second->GetTotalVolume() <= 0) {
                asks_.erase(level_it);
            }
        }
    }
    
    // Remove from the lookup map
    orders_.erase(it);
    
    UpdateBestPrices();
}

double LimitOrderBook::GetBestBid() const {
    return best_bid_;
}

double LimitOrderBook::GetBestAsk() const {
    return best_ask_;
}

double LimitOrderBook::GetMidPrice() const {
    if (best_bid_ > 0 && best_ask_ < std::numeric_limits<double>::max()) {
        return (best_bid_ + best_ask_) / 2.0;
    }
    return 0.0;
}

double LimitOrderBook::GetSpread() const {
    if (best_bid_ > 0 && best_ask_ < std::numeric_limits<double>::max()) {
        return best_ask_ - best_bid_;
    }
    return std::numeric_limits<double>::max();
}

void LimitOrderBook::UpdateBestPrices() {
    best_bid_ = bids_.empty() ? 0.0 : bids_.begin()->first;
    best_ask_ = asks_.empty() ? std::numeric_limits<double>::max() : asks_.begin()->first;
}

double LimitOrderBook::GetOrderImbalance(int levels) const {
    double bid_volume = 0.0;
    double ask_volume = 0.0;
    
    int count = 0;
    for (auto it = bids_.begin(); it != bids_.end() && count < levels; ++it, ++count) {
        bid_volume += it->second->GetTotalVolume();
    }
    
    count = 0;
    for (auto it = asks_.begin(); it != asks_.end() && count < levels; ++it, ++count) {
        ask_volume += it->second->GetTotalVolume();
    }
    
    double total_volume = bid_volume + ask_volume;
    if (total_volume > 0) {
        return (bid_volume - ask_volume) / total_volume;
    }
    return 0.0;
}

std::vector<std::pair<double, double>> LimitOrderBook::GetBidLevels(int count) const {
    std::vector<std::pair<double, double>> levels;
    int i = 0;
    for (auto it = bids_.begin(); it != bids_.end() && i < count; ++it, ++i) {
        levels.emplace_back(it->first, it->second->GetTotalVolume());
    }
    return levels;
}

std::vector<std::pair<double, double>> LimitOrderBook::GetAskLevels(int count) const {
    std::vector<std::pair<double, double>> levels;
    int i = 0;
    for (auto it = asks_.begin(); it != asks_.end() && i < count; ++it, ++i) {
        levels.emplace_back(it->first, it->second->GetTotalVolume());
    }
    return levels;
}

double LimitOrderBook::EstimateMarketImpact(bool is_buy, double quantity) const {
    double remaining_quantity = quantity;
    double weighted_price = 0.0;
    double executed_quantity = 0.0;
    
    if (is_buy) {
        for (auto it = asks_.begin(); it != asks_.end() && remaining_quantity > 0; ++it) {
            double level_quantity = std::min(remaining_quantity, it->second->GetTotalVolume());
            weighted_price += level_quantity * it->first;
            executed_quantity += level_quantity;
            remaining_quantity -= level_quantity;
        }
    } else {
        for (auto it = bids_.begin(); it != bids_.end() && remaining_quantity > 0; ++it) {
            double level_quantity = std::min(remaining_quantity, it->second->GetTotalVolume());
            weighted_price += level_quantity * it->first;
            executed_quantity += level_quantity;
            remaining_quantity -= level_quantity;
        }
    }
    
    if (executed_quantity > 0) {
        double avg_price = weighted_price / executed_quantity;
        
        // Impact is the difference from mid price
        return is_buy ? avg_price - GetMidPrice() : GetMidPrice() - avg_price;
    }
    
    return 0.0;
}

} // namespace microstructure 