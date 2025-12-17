import flet as ft


# === 1. 核心逻辑类 (算法升级) ===
class StockCalculator:
    def __init__(self):
        self.transactions = []
        # 默认费率
        self.rates = {'comm': 0.00025, 'min_comm': 5.0, 'transfer': 0.00001, 'tax': 0.0005}

    def update_rates(self, c, m, t, tf):
        try:
            self.rates['comm'] = float(c)
            self.rates['min_comm'] = float(m)
            self.rates['tax'] = float(t)
            self.rates['transfer'] = float(tf)
            return True
        except:
            return False

    def add_trade(self, code, name, op, price, qty):
        amt = price * qty
        comm = max(amt * self.rates['comm'], self.rates['min_comm'])
        transfer = amt * self.rates['transfer']
        tax = amt * self.rates['tax'] if op == 'sell' else 0
        total_fee = comm + transfer + tax

        trade = {
            "id": len(self.transactions) + 1,
            "code": code, "name": name, "op": op,
            "p": price, "q": qty, "amt": amt,
            "comm": comm, "transfer": transfer, "tax": tax,
            "fee": total_fee,
            "desc": ""
        }
        self.transactions.append(trade)
        return trade

    def delete_trades(self, trades_to_delete):
        for t in trades_to_delete:
            if t in self.transactions:
                self.transactions.remove(t)

    # 【核心修改】双轨制计算：既算摊薄成本，也算实时盈亏
    def get_portfolio_summary(self):
        # 1. 用于计算“摊薄总成本”（做T视角：总进 - 总出）
        diluted_cost_pool = 0.0
        total_qty = 0

        # 2. 用于计算“已实现盈亏”（会计视角：卖出价 - 买入均价）
        realized_pl_accumulator = 0.0

        # 临时字典，用于追踪每只股票的“物理持仓均价”（非摊薄）
        # 格式：{code: {'qty': 0, 'total_cost': 0.0}}
        avg_cost_tracker = {}

        for t in self.transactions:
            code = t['code']
            if code not in avg_cost_tracker:
                avg_cost_tracker[code] = {'qty': 0, 'total_cost': 0.0}

            tracker = avg_cost_tracker[code]

            if t['op'] == 'buy':
                # --- A. 摊薄逻辑 ---
                real_cost = (t['p'] * t['q']) + t['fee']
                diluted_cost_pool += real_cost
                total_qty += t['q']

                # --- B. 均价追踪逻辑 (为了算盈亏) ---
                tracker['total_cost'] += real_cost
                tracker['qty'] += t['q']

                # 更新流水描述
                cur_diluted_avg = diluted_cost_pool / total_qty if total_qty > 0 else 0
                t['desc'] = f"加仓:成本{cur_diluted_avg:.3f}"

            else:  # Sell
                # --- A. 摊薄逻辑 ---
                net_income = (t['p'] * t['q']) - t['fee']
                diluted_cost_pool -= net_income
                total_qty -= t['q']

                # --- B. 均价追踪逻辑 (核心：立即结算盈亏) ---
                # 计算卖出前的持仓均价
                current_avg_price = 0.0
                if tracker['qty'] > 0:
                    current_avg_price = tracker['total_cost'] / tracker['qty']

                # 计算这笔卖出的成本（按均价算）
                cost_of_sold_shares = current_avg_price * t['q']

                # 这笔交易的净利润 = 净收入 - 卖出份额的成本
                trade_profit = net_income - cost_of_sold_shares
                realized_pl_accumulator += trade_profit

                # 更新追踪器
                tracker['qty'] -= t['q']
                tracker['total_cost'] -= cost_of_sold_shares  # 移出已卖出的成本

                # 更新流水描述
                if total_qty <= 0:
                    t['desc'] = f"清仓:盈亏{trade_profit:+.2f}"
                    # 清仓归零防止浮点误差
                    diluted_cost_pool = 0
                    total_qty = 0
                else:
                    cur_diluted_avg = diluted_cost_pool / total_qty
                    t['desc'] = f"减仓:成本{cur_diluted_avg:.3f}"

        return total_qty, diluted_cost_pool, realized_pl_accumulator


# === 2. Flet UI (UI美化版 - 修复颜色报错) ===
def main(page: ft.Page):
    # --- 页面设置 ---
    page.title = "做T助手 Pro"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 15
    page.bgcolor = "#F0F2F5"
    page.scroll = ft.ScrollMode.HIDDEN

    # 模拟手机尺寸
    page.window_width = 393
    page.window_height = 852

    calc = StockCalculator()
    selected_trades = []

    # --- 数据存储 ---
    def save_data():
        try:
            page.client_storage.set("transactions", calc.transactions)
            page.client_storage.set("rates", calc.rates)
        except Exception as e:
            print(f"Save error: {e}")

    def load_data():
        try:
            saved_rates = page.client_storage.get("rates")
            if saved_rates:
                calc.rates = saved_rates
                tf_c.value = str(saved_rates.get('comm', 0.00025))
                tf_m.value = str(saved_rates.get('min_comm', 5.0))
                tf_t.value = str(saved_rates.get('tax', 0.0005))
                tf_tf.value = str(saved_rates.get('transfer', 0.00001))

            saved_tx = page.client_storage.get("transactions")
            if saved_tx:
                calc.transactions = saved_tx
                refresh_dashboard()
                refresh_table()
        except Exception as e:
            print(f"Load error: {e}")

    # --- UI 组件工厂 ---
    def create_card(content, padding=15):
        return ft.Container(
            content=content,
            bgcolor="white",
            padding=padding,
            border_radius=16,
            shadow=ft.BoxShadow(
                blur_radius=10,
                spread_radius=1,
                color="#14000000",
                offset=ft.Offset(0, 4)
            )
        )

    # --- A. 仪表盘 (Dashboard) ---
    txt_hold_qty = ft.Text("0", size=22, weight="w800", color="#2C3E50")
    txt_total_cost = ft.Text("0.00", size=22, weight="w800", color="#2C3E50")
    txt_total_pl = ft.Text("+0.00", size=22, weight="w800", color="#E74C3C")

    def create_stat_col(label, value_ctrl, icon):
        return ft.Column([
            ft.Text(f"{icon} {label}", size=11, color="#7F8C8D", weight="bold"),
            value_ctrl
        ], alignment="center", horizontal_alignment="center", expand=1)

    dashboard = create_card(
        ft.Column([
            ft.Row([
                create_stat_col("持仓(股)", txt_hold_qty, "📦"),
                ft.VerticalDivider(width=1, color="#ECF0F1"),
                create_stat_col("摊薄成本(元)", txt_total_cost, "💰"),
            ]),
            ft.Divider(height=20, color="#ECF0F1"),
            ft.Row([
                create_stat_col("已实现盈亏(元)", txt_total_pl, "🧧"),
            ])
        ], alignment="center")
    )

    # --- B. 输入区 (Input) ---
    def create_input(label, icon, expand=1, kb_type="text"):
        return ft.TextField(
            label=f"{icon} {label}",
            text_size=14,
            height=50,
            content_padding=15,
            border_radius=10,
            bgcolor="#F8F9FA",
            border_color="transparent",
            focused_border_color="#3498DB",
            expand=expand,
            keyboard_type=kb_type
        )

    tf_code = create_input("代码", "🔢", 1)
    tf_name = create_input("名称", "🏷️", 2)
    tf_price = create_input("价格", "💲", 1, "number")
    tf_qty = create_input("数量", "#️⃣", 1, "number")

    def on_trade_click(e):
        op = e.control.data
        if not tf_price.value or not tf_qty.value:
            page.snack_bar = ft.SnackBar(ft.Text("⚠️ 请完善价格和数量"), bgcolor="orange")
            page.snack_bar.open = True
            page.update()
            return
        try:
            p = float(tf_price.value)
            q = int(tf_qty.value)
            calc.update_rates(tf_c.value, tf_m.value, tf_t.value, tf_tf.value)

            last_t = calc.add_trade(tf_code.value, tf_name.value, op, p, q)
            save_data()

            refresh_dashboard()
            refresh_table()
            show_details(last_t)

            tf_price.value = ""
            tf_qty.value = ""
            page.update()
        except Exception as ex:
            print(ex)

    btn_style = ft.ButtonStyle(
        shape=ft.RoundedRectangleBorder(radius=10),
        overlay_color="#1AFFFFFF"
    )

    btn_buy = ft.ElevatedButton(
        content=ft.Row([ft.Text("📉 买入建仓/做T", size=15, weight="bold")], alignment="center"),
        data="buy", on_click=on_trade_click,
        bgcolor="#E74C3C", color="white", height=48, expand=1, style=btn_style
    )
    btn_sell = ft.ElevatedButton(
        content=ft.Row([ft.Text("📈 卖出减仓/止盈", size=15, weight="bold")], alignment="center"),
        data="sell", on_click=on_trade_click,
        bgcolor="#3498DB", color="white", height=48, expand=1, style=btn_style
    )

    input_area = create_card(
        ft.Column([
            ft.Row([tf_code, tf_name], spacing=10),
            ft.Row([tf_price, tf_qty], spacing=10),
            ft.Container(height=5),
            ft.Row([btn_sell, btn_buy], spacing=15)
        ], spacing=10)
    )

    # --- C. 设置区 (Settings) ---
    def create_mini_input(label, val):
        return ft.TextField(
            label=label, value=val,
            width=85, text_size=12, height=40, content_padding=10,
            border_radius=8, bgcolor="#F8F9FA", border_color="transparent"
        )

    tf_c = create_mini_input("佣金", "0.00025")
    tf_m = create_mini_input("起步", "5")
    tf_t = create_mini_input("印花", "0.0005")
    tf_tf = create_mini_input("过户", "0.00001")

    def on_rate_change(e):
        calc.update_rates(tf_c.value, tf_m.value, tf_t.value, tf_tf.value)
        save_data()

    for tf in [tf_c, tf_m, tf_t, tf_tf]: tf.on_change = on_rate_change

    settings = ft.ExpansionTile(
        title=ft.Row([ft.Text("⚙️ 费率设置", size=14, color="#7F8C8D", weight="bold")]),
        controls=[
            ft.Container(
                content=ft.Row([tf_c, tf_m, tf_t, tf_tf], wrap=True, spacing=10, alignment="center"),
                padding=15, bgcolor="white", border_radius=12
            )
        ],
        collapsed_text_color="#95A5A6",
        text_color="#2C3E50"
    )

    # --- D. 交易表格 (Table) ---
    def on_delete_selected(e):
        if not selected_trades: return
        calc.delete_trades(selected_trades)
        selected_trades.clear()
        save_data()
        refresh_dashboard()
        refresh_table()
        clear_details()
        btn_delete_table.visible = False
        page.update()

    btn_delete_table = ft.ElevatedButton(
        "🗑️ 删除选中",
        visible=False,
        on_click=on_delete_selected,
        bgcolor="#E74C3C", color="white", height=30,
        style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=6))
    )

    data_table = ft.DataTable(
        show_checkbox_column=True,
        heading_row_color="#EBF5FB",
        heading_row_height=45,
        data_row_min_height=42,
        data_row_max_height=42,
        column_spacing=20,
        columns=[
            ft.DataColumn(ft.Text("🔢代码", size=12, weight="bold", color="#34495E")),
            ft.DataColumn(ft.Text("🏷️名称", size=12, weight="bold", color="#34495E")),
            ft.DataColumn(ft.Text("🕹️操作", size=12, weight="bold", color="#34495E")),
            ft.DataColumn(ft.Text("💲均价", size=12, weight="bold", color="#34495E"), numeric=True),
            ft.DataColumn(ft.Text("#️⃣数量", size=12, weight="bold", color="#34495E"), numeric=True),
            ft.DataColumn(ft.Text("📈分析", size=12, weight="bold", color="#34495E")),
        ],
        rows=[],
    )

    table_container = create_card(
        ft.Column([
            ft.Row([
                ft.Text("📝 交易流水", weight="bold", size=16, color="#2C3E50"),
                ft.Container(expand=True),
                btn_delete_table
            ], alignment="spaceBetween"),
            ft.Divider(height=10, color="transparent"),
            ft.Container(
                ft.Column([data_table], scroll=ft.ScrollMode.ADAPTIVE, expand=True),
                height=300
            )
        ], spacing=0)
    )

    def on_row_select(e):
        t = e.control.data
        e.control.selected = (e.data == "true")
        if e.data == "true":
            if t not in selected_trades: selected_trades.append(t)
        else:
            if t in selected_trades: selected_trades.remove(t)

        btn_delete_table.visible = len(selected_trades) > 0
        btn_delete_table.text = f"🗑️ 删除({len(selected_trades)})"

        if e.data == "true":
            show_details(t)
        else:
            clear_details()
        page.update()

    def refresh_table():
        data_table.rows.clear()
        selected_trades.clear()
        btn_delete_table.visible = False

        for t in reversed(calc.transactions):
            if t['op'] == 'buy':
                color = "#E74C3C"  # 红
                bg_color = "#FDEDEC"
                op_txt = "买入"
            else:
                color = "#3498DB"  # 蓝
                bg_color = "#EBF5FB"
                op_txt = "卖出"

            data_table.rows.append(
                ft.DataRow(
                    selected=False,
                    on_select_changed=on_row_select,
                    data=t,
                    cells=[
                        ft.DataCell(ft.Text(t['code'], size=12, font_family="monospace")),
                        ft.DataCell(ft.Text(t['name'], size=12)),
                        ft.DataCell(
                            ft.Container(
                                ft.Text(op_txt, color=color, weight="bold", size=11),
                                bgcolor=bg_color, padding=5, border_radius=4
                            )
                        ),
                        ft.DataCell(ft.Text(f"{t['p']:.3f}", size=12, weight="bold")),
                        ft.DataCell(ft.Text(f"{t['q']}", size=12)),
                        ft.DataCell(ft.Text(t.get('desc', ''), size=11, color="#7F8C8D")),
                    ],
                )
            )
        page.update()

    def refresh_dashboard():
        q, c, pl = calc.get_portfolio_summary()
        txt_hold_qty.value = str(q)
        txt_total_cost.value = f"{c:,.2f}"

        # 盈亏颜色逻辑
        if pl > 0:
            txt_total_pl.value = f"+{pl:,.2f}"
            txt_total_pl.color = "#E74C3C"  # 盈红
        elif pl < 0:
            txt_total_pl.value = f"{pl:,.2f}"
            txt_total_pl.color = "#27AE60"  # 亏绿 (A股逻辑)
        else:
            txt_total_pl.value = "0.00"
            txt_total_pl.color = "#2C3E50"
        page.update()

    # --- E. 详情面板 (Details) ---
    def mk_det(label):
        return ft.Text(f"🔹 {label}", size=11, color="#95A5A6")

    def mk_val():
        return ft.Text("--", size=13, weight="bold", color="#2C3E50")

    det_amt = mk_val()
    det_comm = mk_val()
    det_tax = mk_val()
    det_total = ft.Text("--", size=16, weight="bold", color="#E74C3C")

    def clear_details():
        for d in [det_amt, det_comm, det_tax]: d.value = "--"
        det_total.value = "--"
        page.update()

    detail_panel = create_card(
        ft.Column([
            ft.Text("🧐 费用详情分析", weight="bold", size=14, color="#2C3E50"),
            ft.Divider(height=15, color="transparent"),
            ft.Row([
                ft.Column([mk_det("交易金额"), det_amt], expand=1),
                ft.Column([mk_det("实际总费"), det_total], expand=1),
            ]),
            ft.Divider(height=10, color="#F0F3F4"),
            ft.Row([
                ft.Column([mk_det("佣金(含规费)"), det_comm], expand=1),
                ft.Column([mk_det("印花税"), det_tax], expand=1),
            ])
        ])
    )

    def show_details(t):
        det_amt.value = f"{t['amt']:,.2f}"
        det_comm.value = f"{t['comm']:.2f}"
        det_tax.value = f"{t['tax']:.2f}"
        det_total.value = f"{t['fee']:.2f}"
        page.update()

    # --- F. 主布局 ---
    page.add(
        ft.Column([
            dashboard,
            input_area,
            settings,
            table_container,
            detail_panel,
            ft.Container(height=30),
            ft.Text("Build with Flet & Python", size=10, color="#BDC3C7", text_align="center")
        ],
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH
        )
    )

    load_data()


ft.app(target=main)
