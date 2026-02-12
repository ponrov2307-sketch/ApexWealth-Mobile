import flet as ft
import yfinance as yf
import threading
import time

# --- Theme: Obsidian Blue ---
COLORS = {
    "bg": "#050505",
    "card": "#121212",
    "text": "#FFFFFF",
    "sub": "#B0B0B0",
    "accent": "#00E5FF",  # สีฟ้า Apex
    "success": "#00E676",
    "danger": "#FF2A6D",
    "input": "#1C1C1E"
}

def main(page: ft.Page):
    # --- Setup Page ---
    page.title = "Apex Wealth Mobile"
    page.bgcolor = COLORS["bg"]
    page.padding = 20
    page.theme_mode = ft.ThemeMode.DARK
    
    # ตัวแปรเก็บข้อมูล (ใช้ client_storage แทน json ไฟล์)
    # โครงสร้าง: [{"ticker": "VOO", "shares": 5.0, "cost": 400.0}, ...]
    if not page.client_storage.contains_key("portfolio"):
        page.client_storage.set("portfolio", [
            {"ticker": "VOO", "shares": 5.12, "cost": 400.00},
            {"ticker": "NVDA", "shares": 10.0, "cost": 120.50}
        ])
    
    portfolio_data = page.client_storage.get("portfolio")
    fx_rate = 34.50 # ค่าเริ่มต้น

    # --- UI Components ---
    
    # 1. Header & Logo
    header = ft.Row([
        ft.Container(
            content=ft.Icon(ft.icons.ShowChart, color=COLORS["accent"], size=24),
            bgcolor=COLORS["card"], padding=8, border_radius=10
        ),
        ft.Column([
            ft.Text("APEX WEALTH", size=18, weight="bold", color="white"),
            ft.Text("Mobile Portfolio", size=10, color=COLORS["accent"])
        ], spacing=0)
    ], alignment=ft.MainAxisAlignment.START)

    # 2. Dashboard Card
    txt_net_val = ft.Text("฿0.00", size=38, weight="bold", color="white")
    txt_usd_val = ft.Text("≈ $0.00", size=14, color=COLORS["sub"])
    txt_profit = ft.Text("+0.00%", size=14, weight="bold", color=COLORS["success"])
    
    dashboard = ft.Container(
        content=ft.Column([
            ft.Text("มูลค่าพอร์ตสุทธิ", size=12, color=COLORS["accent"], weight="bold"),
            txt_net_val,
            txt_usd_val,
            ft.Divider(color=COLORS["input"]),
            ft.Row([
                ft.Text("กำไร/ขาดทุน", size=12, color=COLORS["sub"]),
                txt_profit
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
        ]),
        bgcolor=COLORS["card"],
        padding=20,
        border_radius=20,
        margin=ft.margin.only(top=20, bottom=20)
    )

    # 3. Asset List (ListView)
    assets_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True)

    def get_country_color(ticker):
        if ".BK" in ticker: return ft.colors.AMBER
        if "-USD" in ticker: return ft.colors.PURPLE
        return ft.colors.BLUE

    def create_asset_item(item, current_price=0):
        # คำนวณกำไรรายตัว
        market_val = current_price * item['shares']
        cost_val = item['cost'] * item['shares']
        profit = market_val - cost_val
        pct = (profit / cost_val * 100) if cost_val > 0 else 0
        
        p_color = COLORS["success"] if pct >= 0 else COLORS["danger"]
        sign = "+" if pct >= 0 else ""

        return ft.Container(
            content=ft.Row([
                # Logo Placeholder
                ft.Container(
                    content=ft.Text(item['ticker'][0], weight="bold", size=18),
                    width=45, height=45, bgcolor=COLORS["input"], border_radius=12,
                    alignment=ft.alignment.center
                ),
                # Name & Shares
                ft.Column([
                    ft.Text(item['ticker'], weight="bold", size=16),
                    ft.Text(f"{item['shares']} units", size=12, color=COLORS["sub"])
                ], expand=True),
                # Price & Profit
                ft.Column([
                    ft.Text(f"${current_price:,.2f}", weight="bold", size=16),
                    ft.Text(f"{sign}{pct:.2f}%", size=12, color=p_color)
                ], alignment=ft.MainAxisAlignment.END, horizontal_alignment=ft.CrossAxisAlignment.END)
            ]),
            bgcolor=COLORS["card"],
            padding=15,
            border_radius=15,
            margin=ft.margin.only(bottom=10),
            on_click=lambda e: open_edit_modal(item) # กดเพื่อแก้ไข
        )

    # --- Logic ---
    def update_ui():
        assets_column.controls.clear()
        
        total_val_usd = 0
        total_cost_usd = 0

        # ดึงราคา (แบบง่ายๆ ทีละตัว เพื่อไม่ให้บล็อค)
        # ในแอปจริงควรดึงแบบ Batch หรือ API เบาๆ
        # ตรงนี้ใช้ Mockup price ถ้าดึงไม่ทัน เพื่อให้ UI ขึ้นก่อน
        
        for item in portfolio_data:
            # *หมายเหตุ: บนมือถือ yfinance อาจจะช้า เราจะใส่ logic ดึงราคาจริงๆ ใน Thread แยก
            # ตรงนี้ขอใส่ราคาหลอกๆ หรือราคาล่าสุดที่จำไว้ก่อน เพื่อความลื่นไหล
            current_price = item.get('last_price', item['cost']) 
            
            total_val_usd += current_price * item['shares']
            total_cost_usd += item['cost'] * item['shares']
            
            assets_column.controls.append(create_asset_item(item, current_price))

        # Update Dashboard
        total_val_thb = total_val_usd * fx_rate
        profit_usd = total_val_usd - total_cost_usd
        profit_pct = (profit_usd / total_cost_usd * 100) if total_cost_usd > 0 else 0
        
        txt_net_val.value = f"฿{total_val_thb:,.2f}"
        txt_usd_val.value = f"≈ ${total_val_usd:,.2f}"
        
        p_sign = "+" if profit_pct >= 0 else ""
        p_color = COLORS["success"] if profit_pct >= 0 else COLORS["danger"]
        txt_profit.value = f"{p_sign}{profit_pct:.2f}% ({p_sign}${profit_usd:,.2f})"
        txt_profit.color = p_color
        
        page.update()

    def price_fetcher_thread():
        # Thread แยกสำหรับดึงราคาจริงๆ
        while True:
            try:
                tickers = [x['ticker'] for x in portfolio_data]
                if tickers:
                    data = yf.download(tickers, period="1d", interval="1m", progress=False)['Close']
                    
                    for item in portfolio_data:
                        t = item['ticker']
                        try:
                            # Handle single vs multiple ticker return structure
                            if len(tickers) == 1:
                                price = float(data.iloc[-1])
                            else:
                                price = float(data[t].iloc[-1])
                            item['last_price'] = price
                        except: pass
                    
                    update_ui()
            except Exception as e:
                print("Error fetching:", e)
            time.sleep(10) # อัปเดตทุก 10 วิ

    # --- Add/Edit Modal (Bottom Sheet) ---
    ticker_input = ft.TextField(label="SYMBOL", bgcolor=COLORS["input"], border_color=COLORS["bg"])
    shares_input = ft.TextField(label="SHARES", bgcolor=COLORS["input"], border_color=COLORS["bg"])
    cost_input = ft.TextField(label="AVG COST ($)", bgcolor=COLORS["input"], border_color=COLORS["bg"])
    
    def save_asset(e):
        try:
            t = ticker_input.value.upper()
            s = float(shares_input.value)
            c = float(cost_input.value)
            
            # Remove old if exists
            for x in portfolio_data:
                if x['ticker'] == t:
                    portfolio_data.remove(x)
                    break
            
            portfolio_data.append({"ticker": t, "shares": s, "cost": c, "last_price": c})
            page.client_storage.set("portfolio", portfolio_data) # Save to phone
            
            page.close_bottom_sheet()
            update_ui()
        except: pass
        
    def delete_asset(e):
        t = ticker_input.value.upper()
        for x in portfolio_data:
            if x['ticker'] == t:
                portfolio_data.remove(x)
                break
        page.client_storage.set("portfolio", portfolio_data)
        page.close_bottom_sheet()
        update_ui()

    save_btn = ft.ElevatedButton("SAVE", bgcolor=COLORS["accent"], color="black", on_click=save_asset, width=150)
    del_btn = ft.TextButton("Delete", on_click=delete_asset)

    bs = ft.BottomSheet(
        ft.Container(
            ft.Column([
                ft.Text("Manage Asset", size=20, weight="bold"),
                ticker_input,
                shares_input,
                cost_input,
                ft.Row([del_btn, save_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
            ], tight=True),
            padding=20,
            bgcolor=COLORS["card"]
        )
    )

    def open_add_modal(e):
        ticker_input.value = ""
        shares_input.value = ""
        cost_input.value = ""
        page.overlay.append(bs)
        bs.open = True
        page.update()

    def open_edit_modal(item):
        ticker_input.value = item['ticker']
        shares_input.value = str(item['shares'])
        cost_input.value = str(item['cost'])
        page.overlay.append(bs)
        bs.open = True
        page.update()

    # --- Floating Action Button ---
    fab = ft.FloatingActionButton(
        icon=ft.icons.ADD,
        bgcolor=COLORS["accent"],
        on_click=open_add_modal
    )

    # Add components to page
    page.add(header, dashboard, ft.Text("Your Assets", weight="bold"), assets_column)
    page.floating_action_button = fab
    
    # Run Init
    update_ui() # First render
    threading.Thread(target=price_fetcher_thread, daemon=True).start()

ft.app(target=main)