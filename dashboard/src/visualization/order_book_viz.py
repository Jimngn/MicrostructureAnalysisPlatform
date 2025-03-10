import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, List, Tuple, Optional
import io
import base64

class OrderBookVisualizer:
    def __init__(self, theme: str = "dark"):
        self.theme = theme
        self.setup_theme()
        
    def setup_theme(self):
        if self.theme == "dark":
            plt.style.use('dark_background')
        else:
            plt.style.use('default')
            
    def create_order_book_snapshot(self, 
                                bid_levels: List[Tuple[float, float]], 
                                ask_levels: List[Tuple[float, float]],
                                mid_price: float,
                                spread: float,
                                order_imbalance: float) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        bid_prices = [level[0] for level in bid_levels]
        bid_volumes = [level[1] for level in bid_levels]
        
        ask_prices = [level[0] for level in ask_levels]
        ask_volumes = [level[1] for level in ask_levels]
        
        ax.barh(bid_prices, bid_volumes, height=bid_prices[0]*0.0002 if bid_prices else 0.01, color='green', alpha=0.6)
        ax.barh(ask_prices, ask_volumes, height=ask_prices[0]*0.0002 if ask_prices else 0.01, color='red', alpha=0.6)
        
        ax.axhline(mid_price, color='white', linestyle='--', alpha=0.5, label=f'Mid Price: {mid_price:.2f}')
        
        max_volume = max(max(bid_volumes) if bid_volumes else 0, max(ask_volumes) if ask_volumes else 0)
        
        bid_color = 'green'
        ask_color = 'red'
        
        if order_imbalance > 0:
            bid_text_color = 'white'
            ask_text_color = 'gray'
        else:
            bid_text_color = 'gray'
            ask_text_color = 'white'
            
        props = dict(boxstyle='round', facecolor='black', alpha=0.7)
        
        imbalance_color = 'green' if order_imbalance > 0 else 'red'
        
        title_text = f'Order Book Snapshot\nMid Price: {mid_price:.2f} | Spread: {spread:.4f} | Imbalance: {order_imbalance:.2f}'
        ax.set_title(title_text)
        
        ax.text(0.98, 0.02, f'Spread: {spread:.4f}', transform=ax.transAxes, fontsize=10,
              verticalalignment='bottom', horizontalalignment='right', bbox=props)
              
        ax.text(0.02, 0.02, f'Imbalance: {order_imbalance:.2f}', transform=ax.transAxes, fontsize=10,
              verticalalignment='bottom', horizontalalignment='left', color=imbalance_color, bbox=props)
              
        ax.set_xlabel('Volume')
        ax.set_ylabel('Price')
        
        max_price = max(max(bid_prices) if bid_prices else mid_price, max(ask_prices) if ask_prices else mid_price)
        min_price = min(min(bid_prices) if bid_prices else mid_price, min(ask_prices) if ask_prices else mid_price)
        price_range = max_price - min_price
        
        ax.set_ylim(min_price - price_range*0.1, max_price + price_range*0.1)
        ax.set_xlim(0, max_volume * 1.1)
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return f'data:image/png;base64,{img_str}'
        
    def create_price_chart(self, 
                         times: List[int], 
                         prices: List[float],
                         volumes: Optional[List[float]] = None,
                         title: str = "Price Chart") -> str:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        dates = [pd.to_datetime(t, unit='ms') for t in times]
        
        ax1.plot(dates, prices, color='#1E88E5', linewidth=1.5)
        
        if volumes:
            ax2.bar(dates, volumes, color='#90CAF9', alpha=0.7)
            ax2.set_ylabel('Volume')
        else:
            ax2.set_visible(False)
            
        ax1.set_title(title)
        ax1.set_ylabel('Price')
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        if len(dates) > 20:
            ax1.xaxis.set_major_locator(mdates.HourLocator())
            
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return f'data:image/png;base64,{img_str}'
        
    def create_order_flow_imbalance_chart(self, 
                                        times: List[int], 
                                        imbalances: List[float],
                                        prices: Optional[List[float]] = None) -> str:
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        dates = [pd.to_datetime(t, unit='ms') for t in times]
        
        cmap = plt.cm.RdYlGn
        norm = plt.Normalize(-1, 1)
        colors = cmap(norm(imbalances))
        
        ax1.bar(dates, imbalances, color=colors, alpha=0.7)
        
        if prices:
            ax2 = ax1.twinx()
            ax2.plot(dates, prices, color='white', linewidth=1.0, alpha=0.7)
            ax2.set_ylabel('Price', color='white')
            
        ax1.set_title('Order Flow Imbalance')
        ax1.set_ylabel('Imbalance')
        
        ax1.set_ylim(-1.1, 1.1)
        ax1.axhline(y=0, color='gray', linestyle='-', linewidth=0.5)
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        if len(dates) > 20:
            ax1.xaxis.set_major_locator(mdates.HourLocator())
            
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return f'data:image/png;base64,{img_str}'
        
    def create_equity_curve(self, timestamps: List[int], equity: List[float]) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        dates = [pd.to_datetime(t, unit='ms') for t in timestamps]
        
        ax.plot(dates, equity, color='#00BCD4', linewidth=1.5)
        
        ax.set_title('Equity Curve')
        ax.set_ylabel('Portfolio Value')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        if len(dates) > 30:
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
            
        initial_equity = equity[0]
        final_equity = equity[-1]
        total_return = (final_equity / initial_equity - 1) * 100
        
        ax.axhline(y=initial_equity, color='gray', linestyle='--', alpha=0.5)
        
        props = dict(boxstyle='round', facecolor='black', alpha=0.7)
        ax.text(0.02, 0.98, f'Return: {total_return:.2f}%', transform=ax.transAxes, fontsize=10,
              verticalalignment='top', horizontalalignment='left', bbox=props)
              
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return f'data:image/png;base64,{img_str}'
        
    def create_drawdown_chart(self, timestamps: List[int], equity: List[float]) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        dates = [pd.to_datetime(t, unit='ms') for t in timestamps]
        
        equity_series = pd.Series(equity, index=dates)
        running_max = equity_series.cummax()
        drawdown = (equity_series / running_max - 1) * 100
        
        ax.fill_between(dates, drawdown, 0, color='#F44336', alpha=0.3)
        ax.plot(dates, drawdown, color='#F44336', linewidth=1.0)
        
        ax.set_title('Drawdown Chart')
        ax.set_ylabel('Drawdown (%)')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        
        if len(dates) > 30:
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates) // 10)))
            
        max_drawdown = drawdown.min()
        
        props = dict(boxstyle='round', facecolor='black', alpha=0.7)
        ax.text(0.02, 0.02, f'Max Drawdown: {max_drawdown:.2f}%', transform=ax.transAxes, fontsize=10,
              verticalalignment='bottom', horizontalalignment='left', color='#F44336', bbox=props)
              
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return f'data:image/png;base64,{img_str}'
        
    def create_heatmap(self, 
                     bid_levels: List[List[Tuple[float, float]]], 
                     ask_levels: List[List[Tuple[float, float]]],
                     timestamps: List[int],
                     mid_prices: List[float]) -> str:
        fig, ax = plt.subplots(figsize=(12, 8))
        
        dates = [pd.to_datetime(t, unit='ms') for t in timestamps]
        
        all_prices = []
        for bids, asks in zip(bid_levels, ask_levels):
            all_prices.extend([p for p, _ in bids])
            all_prices.extend([p for p, _ in asks])
            
        min_price = min(all_prices) if all_prices else min(mid_prices) * 0.99
        max_price = max(all_prices) if all_prices else max(mid_prices) * 1.01
        
        price_range = max_price - min_price
        price_step = price_range / 100
        
        price_levels = np.arange(min_price, max_price, price_step)
        
        heatmap_data = np.zeros((len(price_levels), len(timestamps)))
        
        for t_idx, (bids, asks) in enumerate(zip(bid_levels, ask_levels)):
            for price_idx, price in enumerate(price_levels):
                bid_volume = sum(vol for p, vol in bids if p <= price)
                ask_volume = sum(vol for p, vol in asks if p >= price)
                
                if bid_volume > 0 and ask_volume > 0:
                    imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
                    heatmap_data[price_idx, t_idx] = imbalance
                    
        cmap = plt.cm.RdYlGn
        norm = plt.Normalize(-1, 1)
        
        im = ax.imshow(heatmap_data, aspect='auto', cmap=cmap, norm=norm, 
                     extent=[0, len(timestamps)-1, min_price, max_price], origin='lower')
                     
        ax.plot(range(len(timestamps)), mid_prices, color='white', linewidth=1.0)
        
        ax.set_title('Order Book Depth Heatmap')
        ax.set_ylabel('Price')
        
        ax.set_xticks(range(0, len(timestamps), max(1, len(timestamps) // 10)))
        ax.set_xticklabels([d.strftime('%H:%M') for d in dates[::max(1, len(timestamps) // 10)]])
        
        cbar = fig.colorbar(im, ax=ax)
        cbar.set_label('Order Imbalance')
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return f'data:image/png;base64,{img_str}'
        
    def create_toxic_flow_chart(self, 
                              timestamps: List[int], 
                              toxic_scores: List[float],
                              is_toxic: List[bool],
                              prices: Optional[List[float]] = None) -> str:
        fig, ax1 = plt.subplots(figsize=(10, 6))
        
        dates = [pd.to_datetime(t, unit='ms') for t in timestamps]
        
        colors = ['#F44336' if toxic else '#4CAF50' for toxic in is_toxic]
        
        ax1.bar(dates, toxic_scores, color=colors, alpha=0.7)
        
        if prices:
            ax2 = ax1.twinx()
            ax2.plot(dates, prices, color='white', linewidth=1.0, alpha=0.7)
            ax2.set_ylabel('Price', color='white')
            
        ax1.set_title('Toxic Flow Detection')
        ax1.set_ylabel('Toxicity Score')
        
        ax1.set_ylim(0, 1.1)
        ax1.axhline(y=0.6, color='yellow', linestyle='--', linewidth=1.0, label='Threshold')
        
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        
        if len(dates) > 20:
            ax1.xaxis.set_major_locator(mdates.HourLocator())
            
        ax1.legend()
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return f'data:image/png;base64,{img_str}'
        
    def create_performance_summary(self, performance_metrics: Dict) -> str:
        fig, ax = plt.subplots(figsize=(10, 6))
        
        metrics = {
            'Total Return': performance_metrics.get('total_return', 0) * 100,
            'Annualized Return': performance_metrics.get('annualized_return', 0) * 100,
            'Sharpe Ratio': performance_metrics.get('sharpe_ratio', 0),
            'Max Drawdown': performance_metrics.get('max_drawdown', 0) * 100 * -1,
            'Win Rate': performance_metrics.get('win_rate', 0) * 100
        }
        
        colors = ['#4CAF50' if v > 0 else '#F44336' for v in metrics.values()]
        
        y_pos = np.arange(len(metrics))
        
        ax.barh(y_pos, list(metrics.values()), color=colors)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(list(metrics.keys()))
        
        ax.set_title('Strategy Performance Summary')
        
        for i, v in enumerate(metrics.values()):
            if 'Ratio' in list(metrics.keys())[i]:
                ax.text(v + 0.1, i, f'{v:.2f}', va='center')
            else:
                ax.text(v + 0.1, i, f'{v:.2f}%', va='center')
                
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        plt.close(fig)
        
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        
        return f'data:image/png;base64,{img_str}' 