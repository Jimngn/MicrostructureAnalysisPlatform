use std::collections::{HashMap, BTreeMap};
use std::time::{SystemTime, UNIX_EPOCH};
use serde::{Deserialize, Serialize};
use std::sync::{Arc, Mutex};
use std::sync::atomic::{AtomicUsize, Ordering};
use crossbeam_channel::{bounded, Receiver, Sender};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum MarketMessageType {
    Add,
    Modify,
    Cancel,
    Trade,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct MarketMessage {
    pub timestamp_ns: u64,
    pub symbol: String,
    pub message_type: MarketMessageType,
    pub order_id: Option<String>,
    pub price: Option<f64>,
    pub quantity: Option<f64>,
    pub is_buy: Option<bool>,
    pub trade_id: Option<String>,
}

pub struct MarketDataProcessor {
    sender: Sender<MarketMessage>,
    receiver: Receiver<MarketMessage>,
    message_count: Arc<AtomicUsize>,
    symbol_data: Arc<Mutex<HashMap<String, SymbolData>>>,
}

struct SymbolData {
    last_price: f64,
    daily_volume: f64,
    last_update_time: u64,
    price_history: BTreeMap<u64, f64>,
    volume_history: BTreeMap<u64, f64>,
}

impl MarketDataProcessor {
    pub fn new(buffer_size: usize) -> Self {
        let (sender, receiver) = bounded(buffer_size);
        
        MarketDataProcessor {
            sender,
            receiver,
            message_count: Arc::new(AtomicUsize::new(0)),
            symbol_data: Arc::new(Mutex::new(HashMap::new())),
        }
    }
    
    pub fn submit_message(&self, message: MarketMessage) -> Result<(), String> {
        self.sender.send(message).map_err(|e| e.to_string())
    }
    
    pub fn get_message_count(&self) -> usize {
        self.message_count.load(Ordering::Relaxed)
    }
    
    pub fn start_processing(&self) -> Result<(), String> {
        let receiver = self.receiver.clone();
        let message_count = Arc::clone(&self.message_count);
        let symbol_data = Arc::clone(&self.symbol_data);
        
        std::thread::spawn(move || {
            for message in receiver {
                Self::process_message(&message, &symbol_data);
                message_count.fetch_add(1, Ordering::Relaxed);
            }
        });
        
        Ok(())
    }
    
    fn process_message(message: &MarketMessage, symbol_data: &Arc<Mutex<HashMap<String, SymbolData>>>) {
        let timestamp = message.timestamp_ns;
        
        match message.message_type {
            MarketMessageType::Trade => {
                if let (Some(price), Some(quantity)) = (message.price, message.quantity) {
                    let mut data = symbol_data.lock().unwrap();
                    
                    let symbol_entry = data.entry(message.symbol.clone())
                        .or_insert_with(|| SymbolData {
                            last_price: 0.0,
                            daily_volume: 0.0,
                            last_update_time: 0,
                            price_history: BTreeMap::new(),
                            volume_history: BTreeMap::new(),
                        });
                    
                    symbol_entry.last_price = price;
                    symbol_entry.daily_volume += quantity;
                    symbol_entry.last_update_time = timestamp;
                    
                    let ms_timestamp = timestamp / 1_000_000;
                    symbol_entry.price_history.insert(ms_timestamp, price);
                    
                    *symbol_entry.volume_history.entry(ms_timestamp).or_insert(0.0) += quantity;
                }
            },
            _ => {}
        }
    }
    
    pub fn get_last_price(&self, symbol: &str) -> Option<f64> {
        let data = self.symbol_data.lock().unwrap();
        data.get(symbol).map(|sd| sd.last_price)
    }
    
    pub fn get_daily_volume(&self, symbol: &str) -> Option<f64> {
        let data = self.symbol_data.lock().unwrap();
        data.get(symbol).map(|sd| sd.daily_volume)
    }
    
    pub fn get_price_history(&self, symbol: &str, start_time: u64, end_time: u64) -> Vec<(u64, f64)> {
        let data = self.symbol_data.lock().unwrap();
        if let Some(sd) = data.get(symbol) {
            return sd.price_history.range(start_time..=end_time)
                .map(|(k, v)| (*k, *v))
                .collect();
        }
        Vec::new()
    }
}

pub fn current_time_ns() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_nanos() as u64
} 