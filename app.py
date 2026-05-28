"""
DMG商圏シミュレーションUI (Streamlit)
中心点・半径・獲得率を操作して物件獲得可能件数をシミュレートする
"""
import json
import math
from pathlib import Path

import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

st.set_page_config(page_title="DMG商圏シミュレーション", layout="wide", page_icon="🗺️")

# ─── Load data ───
DATA_PATH = Path(__file__).parent / "data" / "properties.json"

@st.cache_data
def load_properties():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data)
    df = df.dropna(subset=["lat", "lng"]).copy()
    # 戸数を数値化
    df["総戸数_num"] = pd.to_numeric(df["総戸数"], errors="coerce")
    df["平均価格_num"] = pd.to_numeric(df["平均価格"], errors="coerce")
    return df

df = load_properties()

# ─── Preset centers ───
PRESETS = {
    "池袋駅": (35.7295, 139.7109),
    "新宿駅": (35.6896, 139.7006),
    "渋谷駅": (35.6580, 139.7016),
    "東京駅": (35.6812, 139.7671),
    "品川駅": (35.6285, 139.7387),
    "横浜駅": (35.4657, 139.6222),
    "大宮駅": (35.9069, 139.6234),
    "千葉駅": (35.6131, 140.1131),
    "カスタム(住所入力)": None,
}

# ─── Haversine ───
def haversine_km(lat1, lng1, lat2, lng2):
    R = 6371
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp/2)**2 + math.cos(p1) * math.cos(p2) * math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

# ─── Title ───
st.title("DMG商圏シミュレーション")
st.caption("中心点・半径・獲得率を操作して、商圏内の物件獲得可能件数をシミュレート")

# ─── Sidebar controls ───
with st.sidebar:
    st.header("⚙️ シミュレーション条件")

    preset = st.selectbox("📍 中心点プリセット", list(PRESETS.keys()), index=0)
    if PRESETS[preset] is None:
        custom_addr = st.text_input("住所を入力", value="東京都豊島区南池袋1-28-1")
        # Use GSI geocoding (lightweight inline)
        import urllib.parse
        import urllib.request as _ur
        try:
            url = f"https://msearch.gsi.go.jp/address-search/AddressSearch?q={urllib.parse.quote(custom_addr)}"
            with _ur.urlopen(url, timeout=10) as r:
                _d = json.loads(r.read())
                if _d:
                    center_lng, center_lat = _d[0]["geometry"]["coordinates"]
                    st.success(f"取得成功: {_d[0]['properties']['title']}")
                else:
                    st.error("住所が見つかりません。池袋駅で代替表示")
                    center_lat, center_lng = PRESETS["池袋駅"]
        except Exception as e:
            st.error(f"取得失敗: {e}")
            center_lat, center_lng = PRESETS["池袋駅"]
    else:
        center_lat, center_lng = PRESETS[preset]

    st.markdown("---")
    st.subheader("半径 (km)")
    radius_options = st.multiselect(
        "表示する円(複数可)",
        [3, 5, 7, 10, 12, 15, 20, 25, 30],
        default=[5, 10, 15, 20],
    )
    radius_options = sorted(radius_options)

    st.markdown("---")
    st.subheader("📈 獲得率シナリオ")
    capture_rate = st.slider("DMG獲得率 (%)", 0, 50, 10, step=1)

    st.markdown("---")
    st.subheader("🔍 物件フィルター")
    min_units, max_units = st.slider("総戸数レンジ", 0, 1000, (60, 100))
    units_filter_apply = st.checkbox("戸数フィルターを適用", value=True)

# ─── Compute distance + filter ───
df["distance_km"] = df.apply(lambda r: haversine_km(center_lat, center_lng, r["lat"], r["lng"]), axis=1)

df_filtered = df.copy()
if units_filter_apply:
    df_filtered = df_filtered[
        (df_filtered["総戸数_num"] >= min_units) & (df_filtered["総戸数_num"] <= max_units)
    ]

# ─── Summary cards ───
st.subheader(f"集計サマリ (中心点: {preset})")

if not radius_options:
    st.warning("半径を1つ以上選択してください")
else:
    cols = st.columns(len(radius_options))
    summary_data = []
    for i, r_km in enumerate(radius_options):
        in_radius = df_filtered[df_filtered["distance_km"] <= r_km]
        n_properties = len(in_radius)
        n_units = int(in_radius["総戸数_num"].fillna(0).sum())
        n_capturable = round(n_properties * capture_rate / 100, 1)
        with cols[i]:
            st.metric(
                label=f"半径 {r_km}km",
                value=f"{n_properties}物件",
                delta=f"獲得想定 {n_capturable}件",
                delta_color="off",
            )
            st.caption(f"総戸数 {n_units:,}戸")
        summary_data.append({
            "半径(km)": r_km,
            "物件数": n_properties,
            "総戸数": n_units,
            "獲得想定(物件)": n_capturable,
            "獲得想定(戸数)": int(n_units * capture_rate / 100),
        })

    st.markdown("---")

    # ─── Layout: map + table ───
    col_map, col_table = st.columns([3, 2])

    with col_map:
        st.subheader("マップ表示")
        m = folium.Map(location=[center_lat, center_lng], zoom_start=11, tiles="OpenStreetMap")

        # Center marker
        folium.Marker(
            [center_lat, center_lng],
            popup=preset,
            icon=folium.Icon(color="red", icon="star"),
        ).add_to(m)

        # Concentric circles
        circle_colors = ["#1f77b4", "#2ca02c", "#ff7f0e", "#d62728", "#9467bd", "#8c564b"]
        for i, r_km in enumerate(radius_options):
            folium.Circle(
                location=[center_lat, center_lng],
                radius=r_km * 1000,
                color=circle_colors[i % len(circle_colors)],
                fill=False,
                weight=2,
                popup=f"{r_km}km",
                tooltip=f"半径{r_km}km",
            ).add_to(m)

        # Plot properties (limit to max radius shown)
        max_radius = max(radius_options)
        plot_df = df_filtered[df_filtered["distance_km"] <= max_radius].copy()
        for _, row in plot_df.iterrows():
            popup_html = f"""
            <b>{row['物件名']}</b><br>
            事業主: {row['事業主']}<br>
            総戸数: {row['総戸数']}戸<br>
            平均価格: {row['平均価格']}万円<br>
            最寄駅: {row['最寄駅']} 徒歩{row['徒歩']}<br>
            距離: {row['distance_km']:.2f}km
            """
            folium.CircleMarker(
                [row["lat"], row["lng"]],
                radius=4,
                color="#444444",
                fill=True,
                fill_color="#FFA500",
                fill_opacity=0.8,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=row["物件名"],
            ).add_to(m)

        map_key = f"{center_lat}_{center_lng}_{sorted(radius_options)}_{capture_rate}_{min_units}_{max_units}_{units_filter_apply}"
        st_folium(m, width=None, height=600, key=map_key, returned_objects=[])

    with col_table:
        st.subheader("半径別集計")
        st.dataframe(pd.DataFrame(summary_data), hide_index=True, use_container_width=True)

        st.markdown("---")
        st.subheader("獲得率感度分析")
        sens_rates = [5, 10, 15, 20, 30]
        sens_data = []
        for r_km in radius_options:
            in_r = df_filtered[df_filtered["distance_km"] <= r_km]
            row_d = {"半径(km)": r_km, "物件数": len(in_r)}
            for sr in sens_rates:
                row_d[f"{sr}%"] = round(len(in_r) * sr / 100, 1)
            sens_data.append(row_d)
        st.dataframe(pd.DataFrame(sens_data), hide_index=True, use_container_width=True)

    # ─── Detail table ───
    st.markdown("---")
    st.subheader("圏内物件詳細")

    max_radius = max(radius_options) if radius_options else 20
    selected_radius = st.selectbox(
        "表示する半径",
        radius_options,
        index=len(radius_options) - 1,
    )
    detail_df = df_filtered[df_filtered["distance_km"] <= selected_radius].copy()
    detail_df = detail_df.sort_values("distance_km")
    display_cols = ["物件名", "事業主", "総戸数", "平均価格", "最寄駅", "徒歩", "都道府県", "市区町村", "distance_km"]
    detail_df_show = detail_df[display_cols].rename(columns={"distance_km": "距離(km)"})
    detail_df_show["距離(km)"] = detail_df_show["距離(km)"].round(2)
    st.dataframe(detail_df_show, hide_index=True, use_container_width=True, height=400)

    # ─── Download ───
    csv_data = detail_df_show.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 圏内物件リストをCSVでダウンロード",
        data=csv_data,
        file_name=f"DMG_{preset}_{selected_radius}km_物件リスト.csv",
        mime="text/csv",
    )

# ─── Footer ───
st.markdown("---")
st.caption(
    "出典: 加工2024-2025竣工物件リスト | "
    f"全{len(df)}物件をジオコーディング済 | "
    "ジオコーディング: 国土地理院API"
)
