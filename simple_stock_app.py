import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime
from config import FINNHUB_API_KEY

class StockPriceApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Stock Price Tracker")
        self.root.geometry("400x350")
        self.api_key = FINNHUB_API_KEY
        
        # Create main frame
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Symbol input
        ttk.Label(main_frame, text="Enter Stock Symbol:").grid(column=0, row=0, sticky=tk.W, pady=5)
        self.symbol_var = tk.StringVar()
        self.symbol_entry = ttk.Entry(main_frame, width=10, textvariable=self.symbol_var)
        self.symbol_entry.grid(column=1, row=0, sticky=tk.W, pady=5)
        self.symbol_entry.focus()
        
        # Fetch button
        fetch_button = ttk.Button(main_frame, text="Get Price", command=self.fetch_price)
        fetch_button.grid(column=2, row=0, padx=10, pady=5)
        
        # Results frame
        self.result_frame = ttk.LabelFrame(main_frame, text="Stock Information", padding=10)
        self.result_frame.grid(column=0, row=1, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # Results labels
        self.labels = {}
        fields = ["Current Price", "Change", "% Change", "High", "Low", "Previous Close"]
        
        for i, field in enumerate(fields):
            ttk.Label(self.result_frame, text=f"{field}:").grid(column=0, row=i, sticky=tk.W, pady=3)
            self.labels[field] = ttk.Label(self.result_frame, text="--")
            self.labels[field].grid(column=1, row=i, sticky=tk.W, pady=3, padx=10)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def fetch_price(self):
        symbol = self.symbol_var.get().upper()
        if not symbol:
            messagebox.showwarning("Input Error", "Please enter a stock symbol")
            return
        
        self.status_var.set(f"Fetching data for {symbol}...")
        self.root.update_idletasks()
        
        try:
            base_url = "https://finnhub.io/api/v1/quote"
            params = {"symbol": symbol, "token": self.api_key}
            
            response = requests.get(base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            # Update labels with the returned data
            self.labels["Current Price"].config(text=f"${data['c']:.2f}")
            
            change = data['d']
            self.labels["Change"].config(
                text=f"${change:.2f}", 
                foreground="green" if change >= 0 else "red"
            )
            
            percent_change = data['dp']
            self.labels["% Change"].config(
                text=f"{percent_change:.2f}%", 
                foreground="green" if percent_change >= 0 else "red"
            )
            
            self.labels["High"].config(text=f"${data['h']:.2f}")
            self.labels["Low"].config(text=f"${data['l']:.2f}")
            self.labels["Previous Close"].config(text=f"${data['pc']:.2f}")
            
            timestamp = datetime.fromtimestamp(data['t']).strftime('%Y-%m-%d %H:%M:%S')
            self.status_var.set(f"Last updated: {timestamp}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to fetch data: {str(e)}")
            self.status_var.set("Ready")

def main():
    root = tk.Tk()
    app = StockPriceApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
