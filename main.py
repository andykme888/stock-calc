import flet as ft


# === 核心逻辑 (保持不变) ===
class StockCalculator:
    def __init__(self):
        self.transactions = []
        self.portfolio = {}
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
            "code": code, "name": name, "op": op,
            "p": price, "q": qty, "amt": amt,
            "comm": comm, "transfer": transfer, "tax": tax,
            "fee": total_fee,
            "desc": ""
        }
        self.transactions.append(trade)
        return trade

    def get_portfolio_summary(self):
        cost_pool = 0.0
        qty_pool = 0
        for t in self.transactions:
            if t['op'] == 'buy':
                cost_pool += (t['p'] * t['q']) + t['fee']
                qty_pool += t['q']
                t['desc'] = f"加仓:成本{(cost_pool / qty_pool):.3f}"
            else:
                net = (t['p'] * t['q']) - t['fee']
                cost_pool -= net
                qty_pool -= t['q']
                if qty_pool <= 0:
                    t['desc'] = f"清仓:盈亏{-cost_pool:.2f}"
                    cost_pool = 0;
                    qty_pool = 0
                else:
                    t['desc'] = f"减仓:成本{(cost_pool / qty_pool):.3f}"
        return qty_pool, cost_pool


# === Flet UI (手机竖屏适配版) ===
def main(page: ft.Page):
    page.title = "做T神器 Mobile"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 10
    page.bgcolor = "#F3F4F6"
    page.scroll = ft.ScrollMode.HIDDEN  # 主页面不滚动，内部滚动

    # 【关键】设置电脑预览窗口为手机尺寸 (iPhone 14 Pro 逻辑分辨率约为 393x852)
    page.window_width = 393
    page.window_height = 852

    calc = StockCalculator()

    # --- 通用组件 ---
    def create_card(content, padding=10):
        return ft.Container(
            content=content,
            bgcolor="white",
            padding=padding,
            border_radius=12,  # 圆角稍微大一点，更像App
            border=ft.border.all(1, "#E5E7EB"),
            shadow=ft.BoxShadow(blur_radius=5, color="#1A000000")
        )

    # --- 1. 顶部数据卡 (更紧凑) ---
    txt_hold_qty = ft.Text("0", size=24, weight="bold", color="#1F2937")
    txt_total_cost = ft.Text("0.00", size=24, weight="bold", color="#1F2937")

    dashboard = create_card(
        ft.Column([
            ft.Row([
                ft.Column([ft.Text("总持仓(股)", size=12, color="grey"), txt_hold_qty], alignment="center",
                          horizontal_alignment="center", expand=1),
                ft.VerticalDivider(width=1, color="#E5E7EB"),
                ft.Column([ft.Text("摊薄成本(元)", size=12, color="grey"), txt_total_cost], alignment="center",
                          horizontal_alignment="center", expand=1),
            ])
        ], alignment="center")
    )

    # --- 2. 交易输入区 (优化高度) ---
    # 手机上输入框高度设为 40-45 比较舒适，字体 14
    input_style = {"text_size": 14, "height": 45, "content_padding": 10, "border_color": "#D1D5DB"}

    tf_code = ft.TextField(label="代码", expand=1, **input_style)
    tf_name = ft.TextField(label="名称", expand=2, **input_style)
    tf_price = ft.TextField(label="价格", expand=1, keyboard_type="number", **input_style)
    tf_qty = ft.TextField(label="数量", expand=1, keyboard_type="number", **input_style)

    def on_trade_click(e):
        op = e.control.data
        if not tf_price.value or not tf_qty.value:
            page.snack_bar = ft.SnackBar(ft.Text("请输入价格和数量"))
            page.snack_bar.open = True
            page.update()
            return
        try:
            p = float(tf_price.value)
            q = int(tf_qty.value)
            calc.update_rates(tf_c.value, tf_m.value, tf_t.value, tf_tf.value)
            last_t = calc.add_trade(tf_code.value, tf_name.value, op, p, q)
            refresh_table()
            refresh_dashboard()
            show_details(last_t)
            tf_price.value = ""
            tf_qty.value = ""
            page.update()
        except Exception as ex:
            print(ex)

    btn_buy = ft.ElevatedButton("买入", data="buy", on_click=on_trade_click,
                                bgcolor="#DC2626", color="white", height=40, expand=1,
                                style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))
    btn_sell = ft.ElevatedButton("卖出", data="sell", on_click=on_trade_click,
                                 bgcolor="#2563EB", color="white", height=40, expand=1,
                                 style=ft.ButtonStyle(shape=ft.RoundedRectangleBorder(radius=8)))

    input_area = create_card(
        ft.Column([
            ft.Row([tf_code, tf_name], spacing=10),
            ft.Row([tf_price, tf_qty], spacing=10),
            ft.Row([btn_sell, btn_buy], spacing=10)
        ], spacing=10)
    )

    # --- 3. 设置区 (改为 2x2 排列，防止过宽) ---
    setting_style = {"width": None, "expand": 1, "text_size": 12, "height": 35, "content_padding": 5}
    tf_c = ft.TextField(label="佣金", value="0.00025", **setting_style)
    tf_m = ft.TextField(label="起步", value="5", **setting_style)
    tf_t = ft.TextField(label="印花", value="0.0005", **setting_style)
    tf_tf = ft.TextField(label="过户", value="0.00001", **setting_style)

    settings = ft.ExpansionTile(
        title=ft.Text("⚙️ 费率设置", size=14, color="grey"),
        controls=[
            ft.Container(
                content=ft.Column([
                    ft.Row([tf_c, tf_m], spacing=10),  # 第一行
                    ft.Row([tf_t, tf_tf], spacing=10)  # 第二行
                ]),
                padding=10, bgcolor="white"
            )
        ]
    )

    # --- 4. 表格区 (紧凑化) ---
    data_table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("操作", size=12)),
            ft.DataColumn(ft.Text("价", size=12), numeric=True),  # 缩写标题
            ft.DataColumn(ft.Text("量", size=12), numeric=True),
            ft.DataColumn(ft.Text("分析", size=12)),
        ],
        rows=[],
        column_spacing=15,  # 缩小列间距
        heading_row_height=30,
        data_row_min_height=35,
        data_row_max_height=35,
    )

    # 使用 ListView 包裹表格，防止页面撑开，只在区域内滚动
    table_scroll = ft.Column(
        [data_table],
        scroll=ft.ScrollMode.ADAPTIVE,  # 允许横向滚动
        expand=True
    )

    table_container = create_card(
        ft.Column([
            ft.Text("📜 交易流水", weight="bold", size=14),
            ft.Container(table_scroll, height=250)  # 固定高度
        ], spacing=5)
    )

    def refresh_table():
        data_table.rows.clear()
        for t in reversed(calc.transactions):
            color = "red" if t['op'] == 'buy' else "blue"
            op_txt = "买" if t['op'] == 'buy' else "卖"  # 缩写
            # 简化分析文案
            short_desc = t['desc'].replace("加仓:", "").replace("减仓:", "").replace("清仓:", "")

            data_table.rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(op_txt, color=color, weight="bold", size=12)),
                        ft.DataCell(ft.Text(f"{t['p']:.3f}", size=12)),
                        ft.DataCell(ft.Text(f"{t['q']}", size=12)),
                        ft.DataCell(ft.Text(short_desc, size=11, color="grey")),
                    ],
                    on_select_changed=lambda e, t=t: show_details(t)
                )
            )
        page.update()

    def refresh_dashboard():
        q, c = calc.get_portfolio_summary()
        txt_hold_qty.value = str(q)
        txt_total_cost.value = f"{c:,.2f}"

    # --- 5. 详情分析 (2x2 网格布局，完美适配竖屏) ---
    def mk_det(label):
        return ft.Text(label, size=10, color="grey")

    def mk_val():
        return ft.Text("--", size=12, weight="bold")

    det_amt = mk_val()
    det_comm = mk_val()
    det_tax = mk_val()
    det_total = ft.Text("--", size=14, weight="bold", color="red")  # 突出显示

    detail_panel = create_card(
        ft.Column([
            ft.Text("🧐 详情分析", size=12, color="grey"),
            ft.Divider(height=5, color="transparent"),
            # 第一行：交易额 + 实际总费
            ft.Row([
                ft.Column([mk_det("交易金额"), det_amt], expand=1),
                ft.Column([mk_det("实际总费"), det_total], expand=1),
            ]),
            ft.Divider(height=5, color="#F3F4F6"),
            # 第二行：佣金 + 印花税
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

    # --- 页面滚动容器 ---
    # 手机端通常使用一个可滚动的 Column 包裹所有内容
    page.add(
        ft.Column([
            dashboard,
            input_area,
            settings,
            table_container,
            detail_panel,
            ft.Container(height=20)  # 底部留白
        ], scroll=ft.ScrollMode.ADAPTIVE, expand=True)
    )


ft.app(target=main)