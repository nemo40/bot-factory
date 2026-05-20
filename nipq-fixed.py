#!/usr/bin/env python3
# 
#    بوت تمويل MCV  النسخة الاحترافية V5
#    خدماتي (تيك توك/انستجرام/يوتيوب...)  عجلة حظ  هدية يومية/أسبوعية
#    اشتراك إجباري بحد أعضاء  لوحة ترحيب احترافية  أزرار ملونة
#    ليدربورد متطور  رابط هدية  إيموجي مميزة  إشعارات تقدم 10%
#    يتطلب: pyTelegramBotAPI >= 4.32
# 

import os
import telebot
import json
import threading
import time
import sqlite3
import random
import string
import requests
from datetime import datetime, date, timedelta
from telebot import types
from telebot.types import (
    Message, CallbackQuery,
    InlineKeyboardMarkup, InlineKeyboardButton,
)

# ==========================================
#   1. الإعدادات (Config)
# ==========================================
class config:
    BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
    ADMIN_IDS = [6635130346,5436909347]
    SMMPARTY_API_URL = "https://xfollowr.com/api/v2"
    SMMPARTY_API_KEY = "ec9e42cf4fd33d4dd4b9eeec123dd125"
    BOT_NAME = "تمويل بلص"
    BOT_USERNAME = "@eeoeeibot"
    DB_PATH = "plus.db"
    REFERRAL_POINTS = 50
    WELCOME_POINTS = 10
    DAILY_GIFT_POINTS = 5
    WEEKLY_GIFT_POINTS = 50
    POINTS_PER_MEMBER = 1

# ==========================================
#   2. قاعدة البيانات (Database)
# ==========================================
class DictRow(dict):
    """صف يدعم الوصول بالاسم والفهرس الرقمي و .get() معاً."""
    __slots__ = ("_keys",)

    def __init__(self, keys, values):
        super().__init__(zip(keys, values))
        self._keys = keys

    def __getitem__(self, key):
        if isinstance(key, int):
            return super().__getitem__(self._keys[key])
        return super().__getitem__(key)

def _dict_row_factory(cursor, row):
    keys = [col[0] for col in cursor.description]
    return DictRow(keys, row)

class db:
    @classmethod
    def get_conn(cls):
        conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
        conn.row_factory = _dict_row_factory
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @classmethod
    def init_db(cls):
        conn = cls.get_conn()
        c = conn.cursor()

        #  المستخدمون 
        c.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_id            INTEGER UNIQUE NOT NULL,
                username         TEXT DEFAULT '',
                full_name        TEXT DEFAULT '',
                balance          REAL    DEFAULT 0.0,
                points           INTEGER DEFAULT 0,
                referral_code    TEXT    UNIQUE,
                referred_by      INTEGER,
                join_date        TEXT    DEFAULT CURRENT_TIMESTAMP,
                is_banned        INTEGER DEFAULT 0,
                last_daily_gift  TEXT    DEFAULT '',
                last_weekly_gift TEXT    DEFAULT '',
                last_wheel_spin  TEXT    DEFAULT '',
                last_ten_member_gift TEXT DEFAULT ''
            )
        """)

        #  الطلبات 
        c.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                service_id    TEXT    NOT NULL,
                service_name  TEXT    DEFAULT '',
                app_name      TEXT    DEFAULT '',
                link          TEXT    NOT NULL,
                quantity      INTEGER NOT NULL,
                charge        REAL    NOT NULL DEFAULT 0,
                points_used   INTEGER DEFAULT 0,
                status        TEXT    DEFAULT 'pending',
                pending_approval INTEGER DEFAULT 1,
                api_order_id  TEXT,
                site_id       INTEGER DEFAULT NULL,
                notified_done INTEGER DEFAULT 0,
                created_at    TEXT    DEFAULT CURRENT_TIMESTAMP,
                updated_at    TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  مواقع SMM 
        c.execute("""
            CREATE TABLE IF NOT EXISTS smm_sites (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                api_url    TEXT NOT NULL,
                api_key    TEXT NOT NULL,
                is_active  INTEGER DEFAULT 1,
                is_default INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  الإعدادات 
        c.execute("""
            CREATE TABLE IF NOT EXISTS config (
                key   TEXT PRIMARY KEY,
                value TEXT
            )
        """)

        #  القنوات الإجبارية 
        c.execute("""
            CREATE TABLE IF NOT EXISTS mandatory_channels (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id      TEXT UNIQUE NOT NULL,
                channel_name    TEXT NOT NULL,
                channel_url     TEXT NOT NULL,
                target_members  INTEGER DEFAULT 0,
                current_members INTEGER DEFAULT 0,
                added_at        TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  قنوات النقاط 
        c.execute("""
            CREATE TABLE IF NOT EXISTS points_channels (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id    TEXT UNIQUE NOT NULL,
                channel_name  TEXT NOT NULL,
                channel_url   TEXT NOT NULL,
                points_reward INTEGER DEFAULT 20,
                added_at      TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_channel_points (
                user_id    INTEGER NOT NULL,
                channel_id TEXT NOT NULL,
                earned_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, channel_id)
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS mandatory_joins (
                user_id    INTEGER NOT NULL,
                channel_id TEXT NOT NULL,
                joined_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, channel_id)
            )
        """)

        #  الأقسام (Apps) 
        c.execute("""
            CREATE TABLE IF NOT EXISTS apps (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                emoji      TEXT DEFAULT '',
                is_active  INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  خدمات الأقسام 
        c.execute("""
            CREATE TABLE IF NOT EXISTS app_services (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                app_id           INTEGER NOT NULL,
                name             TEXT NOT NULL,
                emoji            TEXT DEFAULT '',
                api_service_id   TEXT NOT NULL,
                site_id          INTEGER DEFAULT NULL,
                points_per_1000  INTEGER NOT NULL DEFAULT 10,
                points_per_unit  INTEGER NOT NULL DEFAULT 10,
                min_qty          INTEGER NOT NULL DEFAULT 100,
                min_10           INTEGER NOT NULL DEFAULT 100,
                max_qty          INTEGER NOT NULL DEFAULT 100000,
                rate_per_1000    REAL    DEFAULT 0.5,
                price_per_1000   REAL    DEFAULT 0.5,
                is_active        INTEGER DEFAULT 1,
                created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (app_id) REFERENCES apps(id) ON DELETE CASCADE
            )
        """)

        #  جوائز الهدايا (Gift Links) 
        c.execute("""
            CREATE TABLE IF NOT EXISTS gift_links (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                code         TEXT UNIQUE NOT NULL,
                points       INTEGER NOT NULL DEFAULT 0,
                max_claims   INTEGER DEFAULT 1,
                current_claims INTEGER DEFAULT 0,
                is_active    INTEGER DEFAULT 1,
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS gift_link_claims (
                user_id    INTEGER NOT NULL,
                code       TEXT NOT NULL,
                claimed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, code)
            )
        """)

        #  التمويلات المكتملة (Showcase) 
        c.execute("""
            CREATE TABLE IF NOT EXISTS completed_fundings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                title       TEXT NOT NULL,
                description TEXT DEFAULT '',
                emoji       TEXT DEFAULT '',
                members     INTEGER DEFAULT 0,
                channel_url TEXT DEFAULT '',
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  أزرار التخصيص (Button Labels/Colors/Visibility) 
        c.execute("""
            CREATE TABLE IF NOT EXISTS button_config (
                btn_key     TEXT PRIMARY KEY,
                btn_label   TEXT DEFAULT '',
                btn_color   TEXT DEFAULT '',
                btn_visible INTEGER DEFAULT 1,
                updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  خطط الاشتراك 
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscription_plans (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                description    TEXT DEFAULT '',
                price          INTEGER NOT NULL DEFAULT 0,
                duration_days  INTEGER DEFAULT 30,
                is_active      INTEGER DEFAULT 1,
                emoji          TEXT DEFAULT '',
                price_stars    INTEGER DEFAULT 0,
                price_vodafone INTEGER DEFAULT 0,
                price_usdt     REAL DEFAULT 0,
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                plan_id     INTEGER NOT NULL,
                start_date  TEXT DEFAULT CURRENT_TIMESTAMP,
                end_date    TEXT,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS subscription_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                plan_id     INTEGER NOT NULL,
                status      TEXT DEFAULT 'pending',
                note        TEXT DEFAULT '',
                method      TEXT DEFAULT 'stars',
                proof       TEXT DEFAULT '',
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  المتجر (Shop Items) 
        c.execute("""
            CREATE TABLE IF NOT EXISTS shop_items (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                emoji       TEXT DEFAULT '',
                price       INTEGER NOT NULL DEFAULT 0,
                stock       INTEGER DEFAULT -1,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS shop_purchases (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                item_id      INTEGER NOT NULL,
                item_name    TEXT DEFAULT '',
                points_used  INTEGER DEFAULT 0,
                status       TEXT DEFAULT 'pending',
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  الريسيلر (Resellers) 
        c.execute("""
            CREATE TABLE IF NOT EXISTS resellers (
                tg_id       INTEGER PRIMARY KEY,
                full_name   TEXT DEFAULT '',
                balance     REAL DEFAULT 0.0,
                discount    INTEGER DEFAULT 10,
                added_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  الأدمنية الديناميكية 
        c.execute("""
            CREATE TABLE IF NOT EXISTS dynamic_admins (
                tg_id      INTEGER PRIMARY KEY,
                full_name  TEXT DEFAULT '',
                added_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  طلبات الشحن (Charge Requests) 
        c.execute("""
            CREATE TABLE IF NOT EXISTS charge_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL    DEFAULT 0,
                points      INTEGER DEFAULT 0,
                method      TEXT    DEFAULT 'vodafone',
                photo_id    TEXT    DEFAULT '',
                status      TEXT    DEFAULT 'pending',
                note        TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  تتبع نسبة تنفيذ الطلبات 
        c.execute("""
            CREATE TABLE IF NOT EXISTS order_progress (
                order_id        INTEGER PRIMARY KEY,
                start_members   INTEGER DEFAULT 0,
                notified_pct    INTEGER DEFAULT 0,
                updated_at      TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  روابط الدعوة 
        c.execute("""
            CREATE TABLE IF NOT EXISTS invite_links (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                code          TEXT UNIQUE NOT NULL,
                points_reward INTEGER NOT NULL,
                max_uses      INTEGER DEFAULT 0,
                current_uses  INTEGER DEFAULT 0,
                is_active     INTEGER DEFAULT 1,
                created_at    TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS user_invite_claims (
                user_id     INTEGER NOT NULL,
                invite_code TEXT NOT NULL,
                claimed_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, invite_code)
            )
        """)

        #  كوبونات الخصم 
        c.execute("""
            CREATE TABLE IF NOT EXISTS coupons (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                code        TEXT    NOT NULL UNIQUE,
                discount    INTEGER NOT NULL DEFAULT 10,
                max_uses    INTEGER DEFAULT -1,
                used_count  INTEGER DEFAULT 0,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS coupon_uses (
                user_id    INTEGER NOT NULL,
                coupon_id  INTEGER NOT NULL,
                used_at    TEXT    DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, coupon_id)
            )
        """)

        #  طلبات شحن الرصيد 
        c.execute("""
            CREATE TABLE IF NOT EXISTS recharge_requests (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                amount      REAL    DEFAULT 0,
                points      INTEGER DEFAULT 0,
                method      TEXT    DEFAULT 'vodafone',
                photo_id    TEXT    DEFAULT '',
                status      TEXT    DEFAULT 'pending',
                note        TEXT    DEFAULT '',
                created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS store_products (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT NOT NULL,
                description TEXT DEFAULT '',
                emoji       TEXT DEFAULT '',
                price       INTEGER NOT NULL DEFAULT 0,
                stock       INTEGER DEFAULT -1,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  طلبات المتجر 
        c.execute("""
            CREATE TABLE IF NOT EXISTS store_orders (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL,
                product_id       INTEGER NOT NULL,
                product_name     TEXT DEFAULT '',
                points_used      INTEGER DEFAULT 0,
                status           TEXT DEFAULT 'pending_approval',
                pending_approval INTEGER DEFAULT 1,
                notified_done    INTEGER DEFAULT 0,
                created_at       TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  سجل الإحالات 
        c.execute("""
            CREATE TABLE IF NOT EXISTS referral_log (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id     INTEGER NOT NULL,
                referred_id     INTEGER NOT NULL,
                points_awarded  INTEGER NOT NULL,
                created_at      TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(referrer_id, referred_id)
            )
        """)

        #  إحالات معلقة (تنتظر اشتراك المُحال في القنوات الإجبارية) 
        c.execute("""
            CREATE TABLE IF NOT EXISTS pending_referrals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                points      INTEGER NOT NULL,
                created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(referrer_id, referred_id)
            )
        """)

        #  جوائز عجلة الحظ 
        c.execute("""
            CREATE TABLE IF NOT EXISTS wheel_prizes (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                points     INTEGER NOT NULL,
                weight     REAL    NOT NULL DEFAULT 10,
                emoji      TEXT    DEFAULT '',
                label      TEXT    DEFAULT '',
                is_active  INTEGER DEFAULT 1,
                created_at TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """)

        n = c.execute("SELECT COUNT(*) FROM wheel_prizes").fetchone()[0]
        if n == 0:
            defaults = [
                (10,  30, '', 'عادي'),
                (25,  20, '', 'جيد'),
                (50,  15, '', 'ممتاز'),
                (100, 10, '', 'رائع'),
                (200,  6, '', 'كبير'),
                (500,  3, '', 'ضخم'),
                (1000, 1, '', 'جائزة كبرى'),
            ]
            for pts, w, em, lbl in defaults:
                c.execute("INSERT INTO wheel_prizes (points,weight,emoji,label) VALUES(?,?,?,?)",
                          (pts, w, em, lbl))

        #  الخدمات المجانية 
        c.execute("""
            CREATE TABLE IF NOT EXISTS free_services (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                name           TEXT NOT NULL,
                description    TEXT DEFAULT '',
                api_service_id TEXT DEFAULT '',
                site_id        INTEGER DEFAULT NULL,
                daily_limit    INTEGER DEFAULT 1,
                min_qty        INTEGER DEFAULT 100,
                max_qty        INTEGER DEFAULT 1000,
                is_active      INTEGER DEFAULT 1,
                created_at     TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS user_free_claims (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                service_id   INTEGER NOT NULL,
                claim_date   TEXT NOT NULL,
                quantity     INTEGER DEFAULT 0,
                link         TEXT DEFAULT '',
                api_order_id TEXT DEFAULT '',
                status       TEXT DEFAULT 'pending',
                created_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  الأدمنية المتعددة 
        c.execute("""
            CREATE TABLE IF NOT EXISTS extra_admins (
                tg_id      INTEGER PRIMARY KEY,
                full_name  TEXT DEFAULT '',
                added_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  قنوات الطلبات 
        c.execute("""
            CREATE TABLE IF NOT EXISTS order_channels (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                channel_id TEXT UNIQUE NOT NULL,
                channel_name TEXT NOT NULL,
                is_active  INTEGER DEFAULT 1,
                added_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  تقييمات الطلبات 
        c.execute("""
            CREATE TABLE IF NOT EXISTS order_ratings (
                order_id   INTEGER PRIMARY KEY,
                user_id    INTEGER NOT NULL,
                stars      INTEGER NOT NULL,
                rated_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        #  خدمات VIP 
        c.execute("""
            CREATE TABLE IF NOT EXISTS mall_apps (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                name       TEXT NOT NULL,
                emoji      TEXT DEFAULT '',
                is_active  INTEGER DEFAULT 1,
                sort_order INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        c.execute("""
            CREATE TABLE IF NOT EXISTS mall_services (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                mall_app_id      INTEGER NOT NULL,
                name             TEXT NOT NULL,
                emoji            TEXT DEFAULT '',
                api_service_id   TEXT NOT NULL,
                site_id          INTEGER DEFAULT NULL,
                points_per_1000  INTEGER NOT NULL DEFAULT 10,
                min_qty          INTEGER NOT NULL DEFAULT 100,
                max_qty          INTEGER NOT NULL DEFAULT 100000,
                rate_per_1000    REAL    DEFAULT 0.5,
                is_active        INTEGER DEFAULT 1,
                created_at       TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (mall_app_id) REFERENCES mall_apps(id) ON DELETE CASCADE
            )
        """)

        #  الإعدادات الافتراضية 
        defaults = {
            "service_id":                "",
            "service_name":              "تمويل قنوات وجروبات",
            "service_min":               "100",
            "service_max":               "100000",
            "updates_channel":           "",
            "support_username":          "@support",
            "bot_active":                "1",
            "rate_per_1000":             "0.5",
            "points_per_1000":           "10",
            "referral_points":           "50",
            "daily_gift_points":         "5",
            "weekly_gift_points":        "50",
            "welcome_points":            "10",
            "wheel_cooldown_hrs":        "6",
            "free_svc_enabled":          "1",
            "free_services_daily_limit": "1",
            "points_charge_info":        "لشحن النقاط تواصل مع الدعم",
            "charge_vodafone_info":      "فودافون كاش: 0123456789",
            "charge_stars_info":         "نجوم: تواصل مع @support",
            "charge_agent_info":         "",
            "charge_agent_username":     "",
            "auto_approve_orders":       "0",
            "terms_text":                "",
            "low_points_alert":          "50",
            "daily_report_enabled":      "1",
            "currency_type":             "points",
            "ban_notify_admin":          "1",
            "custom_welcome_msg":        "",
            "inactive_reminder_enabled": "0",
            "inactive_reminder_days":    "7",
            "inactive_reminder_msg":     "",
        }
        for k, v in defaults.items():
            c.execute("INSERT OR IGNORE INTO config(key,value) VALUES(?,?)", (k, v))

        #  موقع افتراضي (SMMParty) 
        n2 = c.execute("SELECT COUNT(*) FROM smm_sites").fetchone()[0]
        if n2 == 0:
            c.execute("""INSERT INTO smm_sites (name, api_url, api_key, is_active, is_default)
                VALUES (?, ?, ?, 1, 1)""",
                ("SMMParty", "https://smmparty.com/api/v2", "d7ab98d24cdd1c95804bc75b26edc456"))

        conn.commit()
        conn.close()

        #  ترقية قواعد البيانات القديمة (أعمدة جديدة) 
        cls._safe_add_col("users", "last_ten_member_gift", "TEXT DEFAULT ''")
        cls._safe_add_col("app_services", "points_per_unit", "INTEGER NOT NULL DEFAULT 10")
        cls._safe_add_col("app_services", "min_10",          "INTEGER NOT NULL DEFAULT 100")
        cls._safe_add_col("app_services", "price_per_1000",  "REAL DEFAULT 0.5")
        cls._safe_add_col("app_services", "emoji",           "TEXT DEFAULT ''")
        cls._safe_add_col("apps",         "emoji",           "TEXT DEFAULT ''")
        cls._safe_add_col("orders",       "start_members",   "INTEGER DEFAULT -1")
        cls._safe_add_col("subscription_plans", "emoji",          "TEXT DEFAULT ''")
        cls._safe_add_col("subscription_plans", "price_stars",    "INTEGER DEFAULT 0")
        cls._safe_add_col("subscription_plans", "price_vodafone", "INTEGER DEFAULT 0")
        cls._safe_add_col("subscription_plans", "price_usdt",     "REAL DEFAULT 0")
        cls._safe_add_col("subscription_requests", "method",      "TEXT DEFAULT 'stars'")
        cls._safe_add_col("subscription_requests", "proof",       "TEXT DEFAULT ''")
        # مزامنة الأعمدة الجديدة مع القيم القديمة
        try:
            mig = cls.get_conn()
            mig.execute("UPDATE app_services SET points_per_unit=points_per_1000 WHERE points_per_unit=10 AND points_per_1000!=10")
            mig.execute("UPDATE app_services SET min_10=min_qty WHERE min_10=100 AND min_qty!=100")
            mig.execute("UPDATE app_services SET price_per_1000=rate_per_1000 WHERE price_per_1000=0.5 AND rate_per_1000!=0.5")
            mig.commit()
            mig.close()
        except:
            pass
    @classmethod
    def _safe_add_col(cls, table, col, typ):
        try:
            conn = cls.get_conn()
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {typ}")
            conn.commit()
            conn.close()
        except:
            pass

    #  دوال الأعمدة الجديدة (alias) 
    @classmethod
    def get_or_create_user(cls, tg_id, username, full_name, ref_code=None):
        """alias لـ get_or_create"""
        return cls.get_or_create(tg_id, username, full_name, ref_code)

    @classmethod
    def claim_daily_gift(cls, tg_id):
        return cls.claim_daily(tg_id)

    @classmethod
    def claim_weekly_gift(cls, tg_id):
        return cls.claim_weekly(tg_id)

    @classmethod
    def can_spin_wheel(cls, tg_id):
        return cls.can_spin(tg_id)

    @classmethod
    def mark_wheel_spin(cls, tg_id):
        return cls.mark_spin(tg_id)

    @classmethod
    def record_mandatory_join(cls, user_id, ch_id):
        return cls.record_join(user_id, ch_id)

    @classmethod
    def has_earned_channel_points(cls, uid, ch_id):
        return cls.has_channel_pts(uid, ch_id)

    @classmethod
    def mark_channel_points_earned(cls, uid, ch_id):
        return cls.mark_channel_pts(uid, ch_id)

    @classmethod
    def mark_order_notified(cls, oid):
        return cls.mark_notified(oid)

    @classmethod
    def get_leaderboard(cls, limit=10):
        return cls.get_leaderboard_points(limit)

    #  تتبع تقدم الطلبات 
    @classmethod
    def set_order_start_members(cls, order_id, count):
        conn = cls.get_conn()
        conn.execute("""INSERT OR REPLACE INTO order_progress(order_id, start_members, notified_pct, updated_at)
            VALUES(?, ?, COALESCE((SELECT notified_pct FROM order_progress WHERE order_id=?),0), CURRENT_TIMESTAMP)""",
            (order_id, count, order_id))
        # نحفظ أيضاً في orders مباشرة لدعم الـ tracker
        try:
            conn.execute("UPDATE orders SET start_members=? WHERE id=?", (count, order_id))
        except Exception:
            pass
        conn.commit()
        conn.close()

    @classmethod
    def get_order_progress(cls, order_id):
        conn = cls.get_conn()
        r = conn.execute("SELECT notified_pct FROM order_progress WHERE order_id=?", (order_id,)).fetchone()
        conn.close()
        return r["notified_pct"] if r else 0

    @classmethod
    def set_order_notified_pct(cls, order_id, pct):
        conn = cls.get_conn()
        conn.execute("""INSERT OR REPLACE INTO order_progress(order_id, start_members, notified_pct, updated_at)
            VALUES(?, COALESCE((SELECT start_members FROM order_progress WHERE order_id=?),0), ?, CURRENT_TIMESTAMP)""",
            (order_id, order_id, pct))
        conn.commit()
        conn.close()

    @classmethod
    def update_order_status(cls, order_id, status):
        conn = cls.get_conn()
        conn.execute("UPDATE orders SET status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, order_id))
        conn.commit()
        conn.close()

    #  روابط الهدايا 
    @classmethod
    def create_gift_link(cls, code, points, max_claims=1, note=""):
        conn = cls.get_conn()
        try:
            # تحقق إن عمود note موجود وإلا أضفه
            cols = [row[1] for row in conn.execute("PRAGMA table_info(gift_links)").fetchall()]
            if "note" not in cols:
                conn.execute("ALTER TABLE gift_links ADD COLUMN note TEXT DEFAULT ''")
                conn.commit()
            conn.execute("INSERT INTO gift_links(code,points,max_claims,note) VALUES(?,?,?,?)",
                         (code, points, max_claims, note or ""))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @classmethod
    def get_all_gift_links(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM gift_links ORDER BY created_at DESC").fetchall()
        conn.close()
        return r

    @classmethod
    def delete_gift_link(cls, code_or_id):
        conn = cls.get_conn()
        if isinstance(code_or_id, int):
            conn.execute("DELETE FROM gift_links WHERE id=?", (code_or_id,))
        else:
            conn.execute("DELETE FROM gift_links WHERE code=?", (code_or_id,))
        conn.commit()
        conn.close()

    @classmethod
    def toggle_gift_link(cls, code_or_id):
        conn = cls.get_conn()
        if isinstance(code_or_id, int):
            conn.execute("UPDATE gift_links SET is_active=1-is_active WHERE id=?", (code_or_id,))
        else:
            conn.execute("UPDATE gift_links SET is_active=1-is_active WHERE code=?", (code_or_id,))
        conn.commit()
        conn.close()

    @classmethod
    def claim_gift_link(cls, uid, code):
        conn = cls.get_conn()
        lnk = conn.execute("SELECT * FROM gift_links WHERE code=?", (code,)).fetchone()
        if not lnk:
            conn.close()
            return False, 0, "رابط الهدية غير موجود"
        if not lnk["is_active"]:
            conn.close()
            return False, 0, "رابط الهدية غير نشط"
        if lnk["max_claims"] > 0 and lnk["current_claims"] >= lnk["max_claims"]:
            conn.close()
            return False, 0, "انتهت الهدية"
        already = conn.execute("SELECT 1 FROM gift_link_claims WHERE user_id=? AND code=?",
                               (uid, code)).fetchone()
        if already:
            conn.close()
            return False, 0, "استلمت هذه الهدية من قبل"
        pts = lnk["points"]
        try:
            conn.execute("INSERT INTO gift_link_claims(user_id,code) VALUES(?,?)", (uid, code))
            conn.execute("UPDATE gift_links SET current_claims=current_claims+1 WHERE code=?", (code,))
            conn.execute("UPDATE users SET points=points+? WHERE tg_id=?", (pts, uid))
            conn.commit()
        except:
            conn.close()
            return False, 0, "خطأ في الاستلام"
        conn.close()
        return True, pts, ""

    #  كود الدعوة (alias) 
    @classmethod
    def create_invite_link(cls, code, pts, max_uses=0):
        return cls.create_invite(code, pts, max_uses)

    @classmethod
    def get_all_invite_links(cls):
        return cls.get_invites()

    @classmethod
    def delete_invite_link(cls, code):
        return cls.delete_invite(code)

    @classmethod
    def claim_invite_code(cls, uid, code):
        return cls.claim_invite(uid, code)

    #  التمويلات المكتملة (Showcase) 
    @classmethod
    def add_completed_funding(cls, title, description="", emoji="", members=0, channel_url=""):
        conn = cls.get_conn()
        conn.execute("INSERT INTO completed_fundings(title,description,emoji,members,channel_url) VALUES(?,?,?,?,?)",
                     (title, description, emoji, members, channel_url))
        conn.commit()
        conn.close()

    @classmethod
    def get_showcase_fundings(cls, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM completed_fundings" + (" WHERE is_active=1" if only_active else "") + " ORDER BY created_at DESC"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def delete_completed_funding(cls, fid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM completed_fundings WHERE id=?", (fid,))
        conn.commit()
        conn.close()

    @classmethod
    def toggle_completed_funding(cls, fid):
        conn = cls.get_conn()
        conn.execute("UPDATE completed_fundings SET is_active=1-is_active WHERE id=?", (fid,))
        conn.commit()
        conn.close()

    #  تخصيص الأزرار 
    @classmethod
    def btn_label(cls, key, default_text="", default_emoji=""):
        conn = cls.get_conn()
        r = conn.execute("SELECT btn_label FROM button_config WHERE btn_key=?", (key,)).fetchone()
        conn.close()
        lbl = r["btn_label"] if r and r["btn_label"] else default_text
        return lbl

    @classmethod
    def btn_visible(cls, key):
        conn = cls.get_conn()
        r = conn.execute("SELECT btn_visible FROM button_config WHERE btn_key=?", (key,)).fetchone()
        conn.close()
        return (r["btn_visible"] != 0) if r else True

    @classmethod
    def btn_color(cls, key, default="primary"):
        conn = cls.get_conn()
        r = conn.execute("SELECT btn_color FROM button_config WHERE btn_key=?", (key,)).fetchone()
        conn.close()
        return r["btn_color"] if r and r["btn_color"] else default

    @classmethod
    def get_button_label(cls, key):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM button_config WHERE btn_key=?", (key,)).fetchone()
        conn.close()
        # ابحث عن التسمية الافتراضية من STATIC_BUTTON_REGISTRY
        default_label = key
        for _grp, items in STATIC_BUTTON_REGISTRY:
            for cb_key, lbl in items:
                if cb_key == key:
                    default_label = lbl
                    break
        stored_label = (r["btn_label"] if r and r["btn_label"] else default_label)
        btn_color    = (r["btn_color"]  if r and r["btn_color"]  else "primary")
        btn_visible  = (r["btn_visible"] if r else 1)
        parts = stored_label.split(" ", 1)
        if len(parts) == 2 and len(parts[0]) <= 3 and not parts[0].isascii():
            btn_emoji, btn_text = parts[0], parts[1]
        else:
            dparts = default_label.split(" ", 1)
            if len(dparts) == 2 and len(dparts[0]) <= 3:
                btn_emoji = dparts[0]
                btn_text  = dparts[1]
            else:
                btn_emoji = ""
                btn_text  = stored_label
        return {
            "btn_key":    key,
            "btn_label":  stored_label,
            "btn_emoji":  btn_emoji,
            "btn_text":   btn_text,
            "btn_color":  btn_color,
            "btn_visible": btn_visible,
            "is_visible": bool(btn_visible),
        }

    @classmethod
    def get_all_button_labels(cls):
        conn = cls.get_conn()
        db_rows = {r["btn_key"]: r for r in conn.execute("SELECT * FROM button_config").fetchall()}
        conn.close()
        result = []
        for _grp, items in STATIC_BUTTON_REGISTRY:
            for cb_key, default_label in items:
                row = db_rows.get(cb_key)
                btn_color   = (row["btn_color"]  if row and row["btn_color"]  else "primary")
                btn_visible = (row["btn_visible"] if row else 1)
                # استخرج الإيموجي والنص من التسمية المخزنة أو الافتراضية
                stored_label = (row["btn_label"] if row and row["btn_label"] else default_label)
                parts = stored_label.split(" ", 1)
                if len(parts) == 2 and len(parts[0]) <= 3 and not parts[0].isascii():
                    btn_emoji, btn_text = parts[0], parts[1]
                else:
                    # استخرج الإيموجي من التسمية الافتراضية
                    dparts = default_label.split(" ", 1)
                    if len(dparts) == 2 and len(dparts[0]) <= 3:
                        btn_emoji = dparts[0]
                        btn_text  = dparts[1]
                    else:
                        btn_emoji = ""
                        btn_text  = stored_label
                result.append({
                    "btn_key":    cb_key,
                    "btn_label":  stored_label,
                    "btn_emoji":  btn_emoji,
                    "btn_text":   btn_text,
                    "btn_color":  btn_color,
                    "btn_visible": btn_visible,
                    "is_visible": bool(btn_visible),
                })
        return result

    @classmethod
    def set_button_label(cls, key, label):
        conn = cls.get_conn()
        conn.execute("""INSERT INTO button_config(btn_key,btn_label,updated_at)
            VALUES(?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(btn_key) DO UPDATE SET btn_label=excluded.btn_label, updated_at=CURRENT_TIMESTAMP""",
            (key, label))
        conn.commit()
        conn.close()

    @classmethod
    def set_button_color(cls, key, color):
        conn = cls.get_conn()
        conn.execute("""INSERT INTO button_config(btn_key,btn_color,updated_at)
            VALUES(?,?,CURRENT_TIMESTAMP)
            ON CONFLICT(btn_key) DO UPDATE SET btn_color=excluded.btn_color, updated_at=CURRENT_TIMESTAMP""",
            (key, color))
        conn.commit()
        conn.close()

    @classmethod
    def toggle_button_visibility(cls, key):
        conn = cls.get_conn()
        conn.execute("""INSERT INTO button_config(btn_key,btn_visible,updated_at)
            VALUES(?,0,CURRENT_TIMESTAMP)
            ON CONFLICT(btn_key) DO UPDATE SET btn_visible=1-btn_visible, updated_at=CURRENT_TIMESTAMP""",
            (key,))
        conn.commit()
        conn.close()

    #  خطط الاشتراك 
    @classmethod
    def get_subscription_plans(cls, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM subscription_plans" + (" WHERE is_active=1" if only_active else "") + " ORDER BY id"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def get_subscription_plan(cls, pid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM subscription_plans WHERE id=?", (pid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_subscription_plan(cls, name, emoji, days, price_stars=0, price_vodafone=0, price_usdt=0, desc=""):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("""INSERT INTO subscription_plans
            (name,emoji,duration_days,price_stars,price_vodafone,price_usdt,description,price)
            VALUES(?,?,?,?,?,?,?,?)""",
            (name, emoji, days, price_stars, price_vodafone, price_usdt, desc, price_stars))
        pid = cur.lastrowid
        conn.commit()
        conn.close()
        return pid

    @classmethod
    def delete_subscription_plan(cls, pid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM subscription_plans WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    @classmethod
    def toggle_subscription_plan(cls, pid):
        conn = cls.get_conn()
        conn.execute("UPDATE subscription_plans SET is_active=1-is_active WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    @classmethod
    def get_active_subscription(cls, user_id):
        conn = cls.get_conn()
        r = conn.execute("""SELECT s.*, p.name as plan_name, p.emoji as plan_emoji FROM subscriptions s
            JOIN subscription_plans p ON p.id=s.plan_id
            WHERE s.user_id=? AND s.is_active=1 AND (s.end_date IS NULL OR s.end_date > datetime('now'))
            ORDER BY s.created_at DESC LIMIT 1""", (user_id,)).fetchone()
        conn.close()
        return r

    @classmethod
    def create_subscription(cls, user_id, plan_id, method="stars", end_date=None, proof=""):
        from datetime import datetime, timedelta
        if end_date is None:
            plan = cls.get_subscription_plan(plan_id)
            days = plan["duration_days"] if plan else 30
            end = (datetime.now() + timedelta(days=days)).isoformat()
        else:
            end = end_date
        conn = cls.get_conn()
        conn.execute("INSERT INTO subscriptions(user_id,plan_id,end_date) VALUES(?,?,?)",
                     (user_id, plan_id, end))
        conn.commit()
        conn.close()

    @classmethod
    def create_subscription_request(cls, user_id, plan_id, method="stars", proof=""):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO subscription_requests(user_id,plan_id,method,proof) VALUES(?,?,?,?)",
                    (user_id, plan_id, method, proof))
        rid = cur.lastrowid
        conn.commit()
        conn.close()
        return rid

    @classmethod
    def get_subscription_request(cls, rid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM subscription_requests WHERE id=?", (rid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def get_pending_subscription_requests(cls):
        conn = cls.get_conn()
        r = conn.execute("""SELECT sr.*, p.name as plan_name, p.emoji as plan_emoji,
            u.full_name, u.username
            FROM subscription_requests sr
            LEFT JOIN subscription_plans p ON p.id=sr.plan_id
            LEFT JOIN users u ON u.tg_id=sr.user_id
            WHERE sr.status='pending' ORDER BY sr.created_at DESC""").fetchall()
        conn.close()
        return r

    @classmethod
    def update_subscription_request_status(cls, rid, status, note=""):
        conn = cls.get_conn()
        conn.execute("UPDATE subscription_requests SET status=?,note=? WHERE id=?", (status, note, rid))
        conn.commit()
        conn.close()

    #  المتجر 
    @classmethod
    def get_shop_items(cls, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM shop_items" + (" WHERE is_active=1" if only_active else "") + " ORDER BY id"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def get_shop_item(cls, iid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM shop_items WHERE id=?", (iid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_shop_item(cls, name, desc, emoji, price, stock=-1):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO shop_items(name,description,emoji,price,stock) VALUES(?,?,?,?,?)",
                    (name, desc, emoji, price, stock))
        iid = cur.lastrowid
        conn.commit()
        conn.close()
        return iid

    @classmethod
    def delete_shop_item(cls, iid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM shop_items WHERE id=?", (iid,))
        conn.commit()
        conn.close()

    @classmethod
    def buy_shop_item(cls, user_id, item_id, item_name, points):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO shop_purchases(user_id,item_id,item_name,points_used) VALUES(?,?,?,?)",
                    (user_id, item_id, item_name, points))
        pid = cur.lastrowid
        conn.commit()
        conn.close()
        return pid

    @classmethod
    def get_pending_purchases(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM shop_purchases WHERE status='pending' ORDER BY created_at DESC").fetchall()
        conn.close()
        return r

    @classmethod
    def complete_purchase(cls, pid):
        conn = cls.get_conn()
        conn.execute("UPDATE shop_purchases SET status='completed' WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    #  الريسيلر 
    @classmethod
    def get_all_resellers(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM resellers ORDER BY added_at DESC").fetchall()
        conn.close()
        return r

    @classmethod
    def get_reseller(cls, tg_id):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM resellers WHERE tg_id=?", (tg_id,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_reseller(cls, tg_id, full_name="", discount=10):
        conn = cls.get_conn()
        try:
            conn.execute("INSERT INTO resellers(tg_id,full_name,discount) VALUES(?,?,?)", (tg_id, full_name, discount))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @classmethod
    def remove_reseller(cls, tg_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM resellers WHERE tg_id=?", (tg_id,))
        conn.commit()
        conn.close()

    @classmethod
    def transfer_points(cls, from_id, to_id, pts):
        conn = cls.get_conn()
        u = conn.execute("SELECT points FROM users WHERE tg_id=?", (from_id,)).fetchone()
        if not u or u["points"] < pts:
            conn.close()
            return False
        conn.execute("UPDATE users SET points=points-? WHERE tg_id=?", (pts, from_id))
        conn.execute("UPDATE users SET points=points+? WHERE tg_id=?", (pts, to_id))
        conn.commit()
        conn.close()
        return True

    #  الأدمنية الديناميكية 
    @classmethod
    def get_dynamic_admins(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM dynamic_admins").fetchall()
        conn.close()
        return r

    @classmethod
    def is_dynamic_admin(cls, tg_id):
        conn = cls.get_conn()
        r = conn.execute("SELECT 1 FROM dynamic_admins WHERE tg_id=?", (tg_id,)).fetchone()
        conn.close()
        return r is not None

    @classmethod
    def add_dynamic_admin(cls, tg_id, full_name=""):
        conn = cls.get_conn()
        try:
            conn.execute("INSERT INTO dynamic_admins(tg_id,full_name) VALUES(?,?)", (tg_id, full_name))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @classmethod
    def remove_dynamic_admin(cls, tg_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM dynamic_admins WHERE tg_id=?", (tg_id,))
        conn.commit()
        conn.close()

    #  طلبات الشحن (Charge Requests) alias 
    @classmethod
    def create_charge_request(cls, user_id, method, photo_id="", amount=0, pts=0, proof=""):
        """alias مع دعم proof كـ keyword"""
        if proof and not photo_id:
            photo_id = proof
        return cls.create_recharge_request(user_id, method, photo_id, amount)

    @classmethod
    def get_charge_request(cls, rid):
        return cls.get_recharge_request(rid)

    @classmethod
    def get_pending_charges(cls):
        return cls.get_pending_recharges()

    @classmethod
    def update_charge_status(cls, rid, status, points=0, note=""):
        if status == "approved":
            return cls.approve_recharge(rid, points)
        else:
            return cls.reject_recharge(rid, note)

    #  المستخدمون 
    @classmethod
    def get_user(cls, tg_id):
        conn = cls.get_conn()
        u = conn.execute("SELECT * FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        conn.close()
        return u

    @classmethod
    def create_user(cls, tg_id, username, full_name, ref_code=None):
        my_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        referred_by = None
        if ref_code:
            conn = cls.get_conn()
            r = conn.execute("SELECT tg_id FROM users WHERE referral_code=?", (ref_code,)).fetchone()
            conn.close()
            if r and r["tg_id"] != tg_id:
                # ─── حماية من الدعوات الوهمية ───
                # رفض الإحالة إذا كان المُحيل نفسه مشبوهاً (أقل من 3 إحالات مقبولة في السجل)
                # أو إذا كان ID المستخدم الجديد يشبه ID المُحيل (فرق أقل من 1000)
                ref_id = r["tg_id"]
                id_diff = abs(tg_id - ref_id)
                if id_diff > 0:  # ليس نفس الشخص
                    # نقبل الإحالة فقط إذا كان اسم المستخدم أو المعرف يبدو حقيقياً
                    # بوتات تيليجرام لها IDs عالية جداً أو أسماء مشبوهة
                    is_suspicious = (
                        not full_name or
                        len(full_name.strip()) < 2 or
                        (not username and len(str(tg_id)) >= 12)  # IDs طويلة جداً غير طبيعية
                    )
                    if not is_suspicious:
                        referred_by = ref_id
        conn = cls.get_conn()
        try:
            welcome_pts = int(cls.get_config("welcome_points", "10"))
            conn.execute("""INSERT INTO users(tg_id,username,full_name,referral_code,referred_by,points)
                VALUES(?,?,?,?,?,?)""",
                (tg_id, username or '', full_name or '', my_code, referred_by, welcome_pts))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return None
        if referred_by:
            pts = int(cls.get_config("referral_points", "50"))
            try:
                # نخزن الإحالة كـ "معلقة" حتى يشترك المُحال في القنوات الإجبارية
                conn.execute("INSERT OR IGNORE INTO pending_referrals(referrer_id,referred_id,points) VALUES(?,?,?)",
                             (referred_by, tg_id, pts))
                conn.commit()
            except:
                pass
        conn.close()
        return referred_by

    @classmethod
    def award_pending_referral(cls, referred_id):
        """
        يُنفَّذ بعد تحقق اشتراك الشخص في القنوات الإجبارية.
        يمنح المُحيل نقاطه ويحذف السجل المعلق.
        """
        conn = cls.get_conn()
        row = conn.execute(
            "SELECT * FROM pending_referrals WHERE referred_id=?", (referred_id,)
        ).fetchone()
        if not row:
            conn.close()
            return None, 0
        referrer_id = row["referrer_id"]
        pts = row["points"]
        try:
            # منح النقاط للمُحيل وتسجيل الإحالة
            conn.execute(
                "INSERT OR IGNORE INTO referral_log(referrer_id,referred_id,points_awarded) VALUES(?,?,?)",
                (referrer_id, referred_id, pts)
            )
            conn.execute("UPDATE users SET points=points+? WHERE tg_id=?", (pts, referrer_id))
            conn.execute("DELETE FROM pending_referrals WHERE referred_id=?", (referred_id,))
            conn.commit()
        except:
            conn.close()
            return None, 0
        conn.close()
        return referrer_id, pts

    @classmethod
    def get_or_create(cls, tg_id, username, full_name, ref_code=None):
        u = cls.get_user(tg_id)
        if not u:
            rb = cls.create_user(tg_id, username, full_name, ref_code)
            return cls.get_user(tg_id), rb, True
        return u, None, False

    @classmethod
    def update_user(cls, tg_id, **kw):
        if not kw:
            return
        fields = ", ".join(f"{k}=?" for k in kw)
        conn = cls.get_conn()
        conn.execute(f"UPDATE users SET {fields} WHERE tg_id=?", list(kw.values()) + [tg_id])
        conn.commit()
        conn.close()

    @classmethod
    def add_points(cls, tg_id, pts):
        conn = cls.get_conn()
        conn.execute("UPDATE users SET points=points+? WHERE tg_id=?", (pts, tg_id))
        conn.commit()
        conn.close()

    @classmethod
    def deduct_points(cls, tg_id, pts):
        conn = cls.get_conn()
        u = conn.execute("SELECT points FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        if not u or u["points"] < pts:
            conn.close()
            return False
        conn.execute("UPDATE users SET points=points-? WHERE tg_id=?", (pts, tg_id))
        conn.commit()
        new_pts = u["points"] - pts
        conn.close()
        # إشعار انخفاض الرصيد
        try:
            threshold = int(db.get_config("low_points_alert", "50"))
            if threshold > 0 and new_pts <= threshold and u["points"] > threshold:
                threading.Thread(target=_send_low_points_alert,
                                 args=(tg_id, new_pts, threshold), daemon=True).start()
        except:
            pass
        return True

    @classmethod
    def claim_daily(cls, tg_id):
        today = date.today().isoformat()
        conn = cls.get_conn()
        u = conn.execute("SELECT last_daily_gift FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        if not u or u["last_daily_gift"] == today:
            conn.close()
            return False, 0
        pts = int(cls.get_config("daily_gift_points", "5"))
        conn.execute("UPDATE users SET points=points+?,last_daily_gift=? WHERE tg_id=?",
                     (pts, today, tg_id))
        conn.commit()
        conn.close()
        return True, pts

    @classmethod
    def claim_weekly(cls, tg_id):
        today = date.today()
        conn = cls.get_conn()
        u = conn.execute("SELECT last_weekly_gift FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        if not u:
            conn.close()
            return False, 0, 0
        last = u["last_weekly_gift"] or ""
        if last:
            try:
                d = date.fromisoformat(last)
                left = 7 - (today - d).days
                if left > 0:
                    conn.close()
                    return False, 0, left
            except:
                pass
        pts = int(cls.get_config("weekly_gift_points", "50"))
        conn.execute("UPDATE users SET points=points+?,last_weekly_gift=? WHERE tg_id=?",
                     (pts, today.isoformat(), tg_id))
        conn.commit()
        conn.close()
        return True, pts, 0


    @classmethod
    def claim_ten_member_gift(cls, tg_id):
        """يمنح 200 نقطة مقابل 10 إحالات كل 24 ساعة"""
        from datetime import datetime
        conn = cls.get_conn()
        u = conn.execute("SELECT last_ten_member_gift FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        if not u:
            conn.close()
            return False, 0, "user_not_found"
        ref_count = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (tg_id,)).fetchone()[0]
        if ref_count < 10:
            conn.close()
            return False, ref_count, "not_enough"
        last = u["last_ten_member_gift"] or ""
        now = datetime.now()
        if last:
            try:
                last_dt = datetime.fromisoformat(last)
                diff_hours = (now - last_dt).total_seconds() / 3600
                if diff_hours < 24:
                    hours_left = round(24 - diff_hours, 1)
                    conn.close()
                    return False, hours_left, "cooldown"
            except Exception:
                pass
        pts = 200
        conn.execute("UPDATE users SET points=points+?, last_ten_member_gift=? WHERE tg_id=?",
                     (pts, now.isoformat(), tg_id))
        conn.commit()
        conn.close()
        return True, pts, "ok"

    @classmethod
    def can_spin(cls, tg_id):
        hrs = float(cls.get_config("wheel_cooldown_hrs", "6"))
        conn = cls.get_conn()
        u = conn.execute("SELECT last_wheel_spin FROM users WHERE tg_id=?", (tg_id,)).fetchone()
        conn.close()
        if not u or not u["last_wheel_spin"]:
            return True, 0
        try:
            last = datetime.fromisoformat(u["last_wheel_spin"])
            diff = (datetime.now() - last).total_seconds() / 3600
            left = hrs - diff
            if left > 0:
                return False, round(left, 1)
        except:
            pass
        return True, 0

    @classmethod
    def mark_spin(cls, tg_id):
        conn = cls.get_conn()
        conn.execute("UPDATE users SET last_wheel_spin=? WHERE tg_id=?",
                     (datetime.now().isoformat(), tg_id))
        conn.commit()
        conn.close()

    @classmethod
    def get_all_users(cls):
        conn = cls.get_conn()
        u = conn.execute("SELECT * FROM users WHERE is_banned=0").fetchall()
        conn.close()
        return u

    @classmethod
    def get_users_count(cls):
        conn = cls.get_conn()
        n = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        conn.close()
        return n

    @classmethod
    def get_top_referrers(cls, limit=5):
        conn = cls.get_conn()
        rows = conn.execute("""
            SELECT u.tg_id, u.full_name, u.username,
                   COUNT(r.tg_id) as ref_count
            FROM users u
            LEFT JOIN users r ON r.referred_by = u.tg_id
            GROUP BY u.tg_id
            HAVING ref_count > 0
            ORDER BY ref_count DESC
            LIMIT ?
        """, (limit,)).fetchall()
        conn.close()
        return rows

    @classmethod
    def get_referral_count(cls, tg_id):
        conn = cls.get_conn()
        n = conn.execute("SELECT COUNT(*) FROM users WHERE referred_by=?", (tg_id,)).fetchone()[0]
        conn.close()
        return n

    @classmethod
    def get_referral_log_count(cls):
        conn = cls.get_conn()
        n = conn.execute("SELECT COUNT(*) FROM referral_log").fetchone()[0]
        conn.close()
        return n

    #  الطلبات 
    @classmethod
    def create_order(cls, user_id, svc_id, svc_name, link, qty, charge, pts=0, api_id=None, app_name="", site_id=None, points_used=None, api_order_id=None):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("""INSERT INTO orders(user_id,service_id,service_name,app_name,link,
            quantity,charge,points_used,api_order_id,status,site_id,pending_approval) VALUES(?,?,?,?,?,?,?,?,?,?,?,0)""",
            (user_id, svc_id, svc_name, app_name, link, qty, charge,
             points_used if points_used is not None else pts,
             api_order_id if api_order_id is not None else api_id,
             "pending", site_id))
        oid = cur.lastrowid
        conn.commit()
        conn.close()
        return oid

    @classmethod
    def get_user_orders(cls, tg_id, limit=10):
        conn = cls.get_conn()
        rows = conn.execute("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                            (tg_id, limit)).fetchall()
        conn.close()
        return rows

    @classmethod
    def get_user_orders_count(cls, tg_id):
        conn = cls.get_conn()
        n = conn.execute("SELECT COUNT(*) FROM orders WHERE user_id=?", (tg_id,)).fetchone()[0]
        conn.close()
        return n

    @classmethod
    def get_total_completed_orders(cls):
        conn = cls.get_conn()
        n1 = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        n2 = conn.execute("SELECT COUNT(*) FROM user_free_claims").fetchone()[0]
        base = int(cls.get_config("base_orders_count", "0"))
        conn.close()
        return n1 + n2 + base

    @classmethod
    def get_order(cls, oid):
        conn = cls.get_conn()
        o = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        conn.close()
        return o

    @classmethod
    def update_order(cls, oid, status, api_id=None):
        conn = cls.get_conn()
        if api_id:
            conn.execute("UPDATE orders SET status=?,api_order_id=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (status, api_id, oid))
        else:
            conn.execute("UPDATE orders SET status=?,updated_at=CURRENT_TIMESTAMP WHERE id=?",
                         (status, oid))
        conn.commit()
        conn.close()

    @classmethod
    def mark_notified(cls, oid):
        conn = cls.get_conn()
        conn.execute("UPDATE orders SET notified_done=1 WHERE id=?", (oid,))
        conn.commit()
        conn.close()

    @classmethod
    def approve_order(cls, oid):
        """موافقة على طلب SMM وتنفيذه"""
        conn = cls.get_conn()
        conn.execute("UPDATE orders SET pending_approval=0 WHERE id=?", (oid,))
        conn.commit()
        conn.close()

    @classmethod
    def reject_order(cls, oid):
        """رفض طلب SMM واسترداد النقاط"""
        conn = cls.get_conn()
        o = conn.execute("SELECT * FROM orders WHERE id=?", (oid,)).fetchone()
        if o and o["pending_approval"] == 1:
            conn.execute("UPDATE users SET points=points+? WHERE tg_id=?",
                         (o["points_used"], o["user_id"]))
            conn.execute("UPDATE orders SET status='canceled', pending_approval=0 WHERE id=?", (oid,))
            conn.commit()
        conn.close()
        return o

    @classmethod
    def get_pending_orders(cls):
        """طلبات SMM تنتظر الموافقة"""
        conn = cls.get_conn()
        rows = conn.execute(
            "SELECT * FROM orders WHERE pending_approval=1 ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return rows

    #  المتجر 
    @classmethod
    def get_store_products(cls, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM store_products"
        if only_active:
            q += " WHERE is_active=1"
        q += " ORDER BY id"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def get_store_product(cls, pid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM store_products WHERE id=?", (pid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_store_product(cls, name, desc, emoji, price, stock=-1):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO store_products(name,description,emoji,price,stock) VALUES(?,?,?,?,?)",
                    (name, desc, emoji, price, stock))
        pid = cur.lastrowid
        conn.commit()
        conn.close()
        return pid

    @classmethod
    def delete_store_product(cls, pid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM store_products WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    @classmethod
    def toggle_store_product(cls, pid):
        conn = cls.get_conn()
        conn.execute("UPDATE store_products SET is_active=1-is_active WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    @classmethod
    def create_store_order(cls, user_id, product_id, product_name, points):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("""INSERT INTO store_orders(user_id,product_id,product_name,points_used)
                       VALUES(?,?,?,?)""", (user_id, product_id, product_name, points))
        oid = cur.lastrowid
        conn.commit()
        conn.close()
        return oid

    @classmethod
    def get_store_order(cls, oid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM store_orders WHERE id=?", (oid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def approve_store_order(cls, oid):
        conn = cls.get_conn()
        conn.execute("UPDATE store_orders SET pending_approval=0, status='approved' WHERE id=?", (oid,))
        conn.commit()
        conn.close()

    @classmethod
    def reject_store_order(cls, oid):
        conn = cls.get_conn()
        o = conn.execute("SELECT * FROM store_orders WHERE id=?", (oid,)).fetchone()
        if o and o["pending_approval"] == 1:
            conn.execute("UPDATE users SET points=points+? WHERE tg_id=?",
                         (o["points_used"], o["user_id"]))
            conn.execute("UPDATE store_orders SET status='rejected', pending_approval=0 WHERE id=?", (oid,))
            conn.commit()
        conn.close()
        return o

    @classmethod
    def get_pending_store_orders(cls):
        conn = cls.get_conn()
        rows = conn.execute(
            "SELECT * FROM store_orders WHERE pending_approval=1 ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return rows

    @classmethod
    def get_user_store_orders(cls, tg_id, limit=10):
        conn = cls.get_conn()
        rows = conn.execute("SELECT * FROM store_orders WHERE user_id=? ORDER BY created_at DESC LIMIT ?",
                            (tg_id, limit)).fetchall()
        conn.close()
        return rows

    #  طلبات الشحن 
    @classmethod
    def create_recharge_request(cls, user_id, method, photo_id="", amount=0):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO recharge_requests(user_id,method,photo_id,amount) VALUES(?,?,?,?)",
                    (user_id, method, photo_id, amount))
        rid = cur.lastrowid
        conn.commit()
        conn.close()
        return rid

    @classmethod
    def get_recharge_request(cls, rid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM recharge_requests WHERE id=?", (rid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def approve_recharge(cls, rid, points):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM recharge_requests WHERE id=?", (rid,)).fetchone()
        if r and r["status"] == "pending":
            conn.execute("UPDATE users SET points=points+? WHERE tg_id=?", (points, r["user_id"]))
            conn.execute("UPDATE recharge_requests SET status='approved', points=? WHERE id=?", (points, rid))
            conn.commit()
            r = conn.execute("SELECT * FROM recharge_requests WHERE id=?", (rid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def reject_recharge(cls, rid, note=""):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM recharge_requests WHERE id=?", (rid,)).fetchone()
        if r and r["status"] == "pending":
            conn.execute("UPDATE recharge_requests SET status='rejected', note=? WHERE id=?", (note, rid))
            conn.commit()
        conn.close()
        return r

    @classmethod
    def get_pending_recharges(cls):
        conn = cls.get_conn()
        rows = conn.execute(
            "SELECT * FROM recharge_requests WHERE status='pending' ORDER BY created_at DESC"
        ).fetchall()
        conn.close()
        return rows

    #  كوبونات 
    @classmethod
    def get_coupon(cls, code):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM coupons WHERE code=? AND is_active=1", (code.upper(),)).fetchone()
        conn.close()
        return r

    @classmethod
    def get_coupon_by_id(cls, cid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM coupons WHERE id=?", (cid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def get_all_coupons(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM coupons ORDER BY created_at DESC").fetchall()
        conn.close()
        return r

    @classmethod
    def add_coupon(cls, code, discount, max_uses=-1):
        conn = cls.get_conn()
        try:
            conn.execute("INSERT INTO coupons(code,discount,max_uses) VALUES(?,?,?)",
                         (code.upper(), discount, max_uses))
            conn.commit()
            result = True
        except:
            result = False
        conn.close()
        return result

    @classmethod
    def delete_coupon(cls, cid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM coupons WHERE id=?", (cid,))
        conn.commit()
        conn.close()

    @classmethod
    def toggle_coupon(cls, cid):
        conn = cls.get_conn()
        conn.execute("UPDATE coupons SET is_active=1-is_active WHERE id=?", (cid,))
        conn.commit()
        conn.close()

    @classmethod
    def user_used_coupon(cls, user_id, coupon_id):
        conn = cls.get_conn()
        r = conn.execute("SELECT 1 FROM coupon_uses WHERE user_id=? AND coupon_id=?",
                         (user_id, coupon_id)).fetchone()
        conn.close()
        return r is not None

    @classmethod
    def mark_coupon_used(cls, user_id, coupon_id):
        conn = cls.get_conn()
        conn.execute("INSERT OR IGNORE INTO coupon_uses(user_id,coupon_id) VALUES(?,?)",
                     (user_id, coupon_id))
        conn.execute("UPDATE coupons SET used_count=used_count+1 WHERE id=?", (coupon_id,))
        conn.commit()
        conn.close()

    #  ليدربورد 
    @classmethod
    def get_leaderboard_points(cls, limit=10):
        conn = cls.get_conn()
        r = conn.execute(
            "SELECT tg_id, full_name, username, points FROM users ORDER BY points DESC LIMIT ?",
            (limit,)).fetchall()
        conn.close()
        return r

    @classmethod
    def get_leaderboard_orders(cls, limit=10):
        conn = cls.get_conn()
        r = conn.execute(
            "SELECT user_id, COUNT(*) as cnt, SUM(points_used) as total_pts FROM orders "
            "GROUP BY user_id ORDER BY cnt DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return r

    #  إحصائيات التقرير 
    @classmethod
    def get_daily_stats(cls):
        conn = cls.get_conn()
        today = datetime.now().strftime("%Y-%m-%d")
        stats = {}
        stats["new_users"]    = conn.execute(
            "SELECT COUNT(*) FROM users WHERE created_at LIKE ?", (today+"%",)).fetchone()[0]
        stats["total_users"]  = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        stats["new_orders"]   = conn.execute(
            "SELECT COUNT(*) FROM orders WHERE created_at LIKE ?", (today+"%",)).fetchone()[0]
        stats["total_orders"] = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        stats["points_spent"] = conn.execute(
            "SELECT COALESCE(SUM(points_used),0) FROM orders WHERE created_at LIKE ?",
            (today+"%",)).fetchone()[0]
        stats["store_orders"] = conn.execute(
            "SELECT COUNT(*) FROM store_orders WHERE created_at LIKE ?", (today+"%",)).fetchone()[0]
        stats["recharges"]    = conn.execute(
            "SELECT COUNT(*) FROM recharge_requests WHERE status='approved' AND created_at LIKE ?",
            (today+"%",)).fetchone()[0]
        conn.close()
        return stats

    @classmethod
    def get_orders_stats(cls):
        conn = cls.get_conn()
        total   = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        today   = conn.execute("SELECT COUNT(*) FROM orders WHERE DATE(created_at)=DATE('now')").fetchone()[0]
        revenue = conn.execute("SELECT COALESCE(SUM(charge),0) FROM orders").fetchone()[0]
        trev    = conn.execute("SELECT COALESCE(SUM(charge),0) FROM orders WHERE DATE(created_at)=DATE('now')").fetchone()[0]
        tpts    = conn.execute("SELECT COALESCE(SUM(points_used),0) FROM orders").fetchone()[0]
        conn.close()
        return total, today, revenue, trev, tpts

    #  الإعدادات 
    @classmethod
    def get_config(cls, key, default=""):
        conn = cls.get_conn()
        r = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
        conn.close()
        return r["value"] if r else default

    @classmethod
    def set_config(cls, key, value):
        conn = cls.get_conn()
        conn.execute("INSERT OR REPLACE INTO config(key,value) VALUES(?,?)", (key, value))
        conn.commit()
        conn.close()

    @classmethod
    def get_all_config(cls):
        conn = cls.get_conn()
        rows = conn.execute("SELECT key, value FROM config ORDER BY key").fetchall()
        conn.close()
        return rows

    #  رموز تعبيرية مميزة للأزرار (Custom Emoji IDs) 
    @classmethod
    def get_btn_emoji(cls, cb):
        """جلب ID الرمز التعبيري المميز المخصص لزر معين (callback_data)."""
        if not cb:
            return ""
        return cls.get_config(f"btn_emoji:{cb}", "")

    @classmethod
    def set_btn_emoji(cls, cb, emoji_id):
        """ضبط ID الرمز التعبيري لزر معين. لو emoji_id فارغ يتم الحذف."""
        if not cb:
            return
        key = f"btn_emoji:{cb}"
        if emoji_id:
            cls.set_config(key, str(emoji_id))
        else:
            conn = cls.get_conn()
            conn.execute("DELETE FROM config WHERE key=?", (key,))
            conn.commit()
            conn.close()

    @classmethod
    def list_btn_emojis(cls):
        """إرجاع dict {cb: emoji_id} لكل الأزرار المضبوطة."""
        conn = cls.get_conn()
        rows = conn.execute(
            "SELECT key, value FROM config WHERE key LIKE 'btn_emoji:%'"
        ).fetchall()
        conn.close()
        prefix = "btn_emoji:"
        return {r["key"][len(prefix):]: r["value"] for r in rows if r["value"]}

    @classmethod
    def clear_all_btn_emojis(cls):
        """مسح كل رموز الأزرار التعبيرية المميزة."""
        conn = cls.get_conn()
        conn.execute("DELETE FROM config WHERE key LIKE 'btn_emoji:%'")
        conn.commit()
        conn.close()

    #  القنوات الإجبارية 
    @classmethod
    def get_mandatory_channels(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM mandatory_channels").fetchall()
        conn.close()
        return r

    @classmethod
    def add_mandatory_channel(cls, ch_id, name, url, target=0):
        conn = cls.get_conn()
        try:
            conn.execute("""INSERT INTO mandatory_channels(channel_id,channel_name,channel_url,target_members,current_members)
                VALUES(?,?,?,?,0)""", (ch_id, name, url, target))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @classmethod
    def remove_mandatory_channel(cls, ch_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM mandatory_channels WHERE channel_id=?", (ch_id,))
        conn.commit()
        conn.close()

    @classmethod
    def record_join(cls, user_id, ch_id):
        conn = cls.get_conn()
        try:
            cur = conn.execute("INSERT OR IGNORE INTO mandatory_joins(user_id,channel_id) VALUES(?,?)",
                               (user_id, ch_id))
            if cur.rowcount > 0:
                conn.execute("UPDATE mandatory_channels SET current_members=current_members+1 WHERE channel_id=?", (ch_id,))
                conn.commit()
                r = conn.execute("SELECT target_members,current_members FROM mandatory_channels WHERE channel_id=?",
                                 (ch_id,)).fetchone()
                if r and r["target_members"] > 0 and r["current_members"] >= r["target_members"]:
                    conn.execute("DELETE FROM mandatory_channels WHERE channel_id=?", (ch_id,))
                    conn.commit()
        except:
            pass
        conn.close()

    #  قنوات النقاط 
    @classmethod
    def get_points_channels(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM points_channels").fetchall()
        conn.close()
        return r

    @classmethod
    def add_points_channel(cls, ch_id, name, url, pts):
        conn = cls.get_conn()
        try:
            conn.execute("INSERT INTO points_channels(channel_id,channel_name,channel_url,points_reward) VALUES(?,?,?,?)",
                         (ch_id, name, url, pts))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @classmethod
    def remove_points_channel(cls, ch_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM points_channels WHERE channel_id=?", (ch_id,))
        conn.commit()
        conn.close()

    @classmethod
    def has_channel_pts(cls, uid, ch_id):
        conn = cls.get_conn()
        r = conn.execute("SELECT 1 FROM user_channel_points WHERE user_id=? AND channel_id=?",
                         (uid, ch_id)).fetchone()
        conn.close()
        return r is not None

    @classmethod
    def mark_channel_pts(cls, uid, ch_id):
        conn = cls.get_conn()
        conn.execute("INSERT OR IGNORE INTO user_channel_points(user_id,channel_id) VALUES(?,?)", (uid, ch_id))
        conn.commit()
        conn.close()

    #  قنوات الطلبات 
    @classmethod
    def get_order_channels(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM order_channels WHERE is_active=1").fetchall()
        conn.close()
        return r

    @classmethod
    def add_order_channel(cls, ch_id, name):
        conn = cls.get_conn()
        try:
            conn.execute("INSERT INTO order_channels(channel_id,channel_name) VALUES(?,?)", (ch_id, name))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @classmethod
    def remove_order_channel(cls, ch_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM order_channels WHERE channel_id=?", (ch_id,))
        conn.commit()
        conn.close()

    #  أكواد الدعوة 
    @classmethod
    def create_invite(cls, code, pts, max_uses=0):
        conn = cls.get_conn()
        try:
            conn.execute("INSERT INTO invite_links(code,points_reward,max_uses) VALUES(?,?,?)",
                         (code, pts, max_uses))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @classmethod
    def get_invites(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM invite_links ORDER BY created_at DESC").fetchall()
        conn.close()
        return r

    @classmethod
    def delete_invite(cls, code):
        conn = cls.get_conn()
        conn.execute("DELETE FROM invite_links WHERE code=?", (code,))
        conn.commit()
        conn.close()

    @classmethod
    def claim_invite(cls, uid, code):
        conn = cls.get_conn()
        lnk = conn.execute("SELECT * FROM invite_links WHERE code=?", (code,)).fetchone()
        if not lnk:
            conn.close()
            return False, 0, "الكود غير موجود"
        if not lnk["is_active"]:
            conn.close()
            return False, 0, "الكود غير نشط"
        if lnk["max_uses"] > 0 and lnk["current_uses"] >= lnk["max_uses"]:
            conn.close()
            return False, 0, "الكود وصل للحد الأقصى"
        claimed = conn.execute("SELECT 1 FROM user_invite_claims WHERE user_id=? AND invite_code=?",
                               (uid, code)).fetchone()
        if claimed:
            conn.close()
            return False, 0, "استخدمت هذا الكود من قبل"
        pts = lnk["points_reward"]
        try:
            conn.execute("INSERT INTO user_invite_claims(user_id,invite_code) VALUES(?,?)", (uid, code))
            conn.execute("UPDATE invite_links SET current_uses=current_uses+1 WHERE code=?", (code,))
            conn.execute("UPDATE users SET points=points+? WHERE tg_id=?", (pts, uid))
            conn.commit()
        except sqlite3.IntegrityError:
            conn.close()
            return False, 0, "استخدمت هذا الكود من قبل"
        conn.close()
        return True, pts, ""

    #  الأقسام 
    @classmethod
    def get_apps(cls, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM apps" + (" WHERE is_active=1" if only_active else "") + " ORDER BY sort_order,id"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def get_app(cls, app_id):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM apps WHERE id=?", (app_id,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_app(cls, name, emoji=""):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO apps(name,emoji) VALUES(?,?)", (name, emoji))
        aid = cur.lastrowid
        conn.commit()
        conn.close()
        return aid

    @classmethod
    def update_app(cls, app_id, name=None, emoji=None):
        fields = []
        params = []
        if name is not None:
            fields.append("name=?")
            params.append(name)
        if emoji is not None:
            fields.append("emoji=?")
            params.append(emoji)
        if not fields:
            return
        params.append(app_id)
        conn = cls.get_conn()
        conn.execute(f"UPDATE apps SET {', '.join(fields)} WHERE id=?", params)
        conn.commit()
        conn.close()

    @classmethod
    def delete_app(cls, app_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM app_services WHERE app_id=?", (app_id,))
        conn.execute("DELETE FROM apps WHERE id=?", (app_id,))
        conn.commit()
        conn.close()

    #  خدمات الأقسام 
    @classmethod
    def get_app_services(cls, app_id, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM app_services WHERE app_id=?" + (" AND is_active=1" if only_active else "") + " ORDER BY id"
        r = conn.execute(q, (app_id,)).fetchall()
        conn.close()
        return r

    @classmethod
    def get_service(cls, sid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM app_services WHERE id=?", (sid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_service(cls, app_id, name, emoji, api_id, pts_per_1000, mn, mx, rate, site_id=None):
        conn = cls.get_conn()
        conn.execute("""INSERT INTO app_services(app_id,name,emoji,api_service_id,points_per_1000,min_qty,max_qty,rate_per_1000,site_id)
            VALUES(?,?,?,?,?,?,?,?,?)""", (app_id, name, emoji, api_id, pts_per_1000, mn, mx, rate, site_id))
        conn.commit()
        conn.close()

    @classmethod
    def update_service(cls, sid, name=None, emoji=None):
        fields = []
        params = []
        if name is not None:
            fields.append("name=?")
            params.append(name)
        if emoji is not None:
            fields.append("emoji=?")
            params.append(emoji)
        if not fields:
            return
        params.append(sid)
        conn = cls.get_conn()
        conn.execute(f"UPDATE app_services SET {', '.join(fields)} WHERE id=?", params)
        conn.commit()
        conn.close()

    @classmethod
    def delete_service(cls, sid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM app_services WHERE id=?", (sid,))
        conn.commit()
        conn.close()

    #  خدمات VIP 
    @classmethod
    def get_mall_apps(cls, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM mall_apps" + (" WHERE is_active=1" if only_active else "") + " ORDER BY sort_order,id"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def get_mall_app(cls, app_id):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM mall_apps WHERE id=?", (app_id,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_mall_app(cls, name, emoji=""):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO mall_apps(name,emoji) VALUES(?,?)", (name, emoji))
        aid = cur.lastrowid
        conn.commit()
        conn.close()
        return aid

    @classmethod
    def delete_mall_app(cls, app_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM mall_services WHERE mall_app_id=?", (app_id,))
        conn.execute("DELETE FROM mall_apps WHERE id=?", (app_id,))
        conn.commit()
        conn.close()

    @classmethod
    def get_mall_services(cls, app_id, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM mall_services WHERE mall_app_id=?" + (" AND is_active=1" if only_active else "") + " ORDER BY id"
        r = conn.execute(q, (app_id,)).fetchall()
        conn.close()
        return r

    @classmethod
    def get_mall_service(cls, sid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM mall_services WHERE id=?", (sid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_mall_service(cls, app_id, name, emoji, api_id, pts_per_1000, mn, mx, rate, site_id=None):
        conn = cls.get_conn()
        conn.execute("""INSERT INTO mall_services(mall_app_id,name,emoji,api_service_id,points_per_1000,min_qty,max_qty,rate_per_1000,site_id)
            VALUES(?,?,?,?,?,?,?,?,?)""", (app_id, name, emoji, api_id, pts_per_1000, mn, mx, rate, site_id))
        conn.commit()
        conn.close()

    @classmethod
    def delete_mall_service(cls, sid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM mall_services WHERE id=?", (sid,))
        conn.commit()
        conn.close()

    #  مواقع SMM 
    @classmethod
    def get_smm_sites(cls, only_active=False):
        conn = cls.get_conn()
        q = "SELECT * FROM smm_sites" + (" WHERE is_active=1" if only_active else "") + " ORDER BY id"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def get_smm_site(cls, site_id):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM smm_sites WHERE id=?", (site_id,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_smm_site(cls, name, api_url, api_key):
        conn = cls.get_conn()
        cur = conn.cursor()
        cur.execute("INSERT INTO smm_sites(name,api_url,api_key) VALUES(?,?,?)", (name, api_url, api_key))
        sid = cur.lastrowid
        conn.commit()
        conn.close()
        return sid

    @classmethod
    def delete_smm_site(cls, site_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM smm_sites WHERE id=?", (site_id,))
        conn.commit()
        conn.close()

    @classmethod
    def toggle_smm_site(cls, site_id):
        conn = cls.get_conn()
        conn.execute("UPDATE smm_sites SET is_active=1-is_active WHERE id=?", (site_id,))
        conn.commit()
        conn.close()

    #  عجلة الحظ 
    @classmethod
    def get_wheel_prizes(cls, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM wheel_prizes" + (" WHERE is_active=1" if only_active else "") + " ORDER BY points ASC"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def add_wheel_prize(cls, pts, weight, emoji="", label=""):
        conn = cls.get_conn()
        conn.execute("INSERT INTO wheel_prizes(points,weight,emoji,label) VALUES(?,?,?,?)",
                     (pts, weight, emoji, label))
        conn.commit()
        conn.close()

    @classmethod
    def delete_wheel_prize(cls, pid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM wheel_prizes WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    @classmethod
    def toggle_wheel_prize(cls, pid):
        conn = cls.get_conn()
        conn.execute("UPDATE wheel_prizes SET is_active=1-is_active WHERE id=?", (pid,))
        conn.commit()
        conn.close()

    #  الخدمات المجانية 
    @classmethod
    def get_free_services(cls, only_active=True):
        conn = cls.get_conn()
        q = "SELECT * FROM free_services" + (" WHERE is_active=1" if only_active else "") + " ORDER BY id"
        r = conn.execute(q).fetchall()
        conn.close()
        return r

    @classmethod
    def get_free_service(cls, sid):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM free_services WHERE id=?", (sid,)).fetchone()
        conn.close()
        return r

    @classmethod
    def add_free_service(cls, name, desc, api_id, daily_limit, mn, mx, site_id=None):
        conn = cls.get_conn()
        conn.execute("""INSERT INTO free_services(name,description,api_service_id,daily_limit,min_qty,max_qty,site_id)
            VALUES(?,?,?,?,?,?,?)""", (name, desc, api_id, daily_limit, mn, mx, site_id))
        conn.commit()
        conn.close()

    @classmethod
    def delete_free_service(cls, sid):
        conn = cls.get_conn()
        conn.execute("DELETE FROM free_services WHERE id=?", (sid,))
        conn.commit()
        conn.close()

    @classmethod
    def get_free_claim_count_today(cls, uid, sid):
        today = date.today().isoformat()
        conn = cls.get_conn()
        n = conn.execute("SELECT COUNT(*) FROM user_free_claims WHERE user_id=? AND service_id=? AND claim_date=?",
                         (uid, sid, today)).fetchone()[0]
        conn.close()
        return n

    @classmethod
    def get_free_claim_count_today_total(cls, uid):
        today = date.today().isoformat()
        conn = cls.get_conn()
        n = conn.execute("SELECT COUNT(*) FROM user_free_claims WHERE user_id=? AND claim_date=?",
                         (uid, today)).fetchone()[0]
        conn.close()
        return n

    @classmethod
    def add_free_claim(cls, uid, sid, qty, link, api_id="", status="pending"):
        today = date.today().isoformat()
        conn = cls.get_conn()
        conn.execute("""INSERT INTO user_free_claims(user_id,service_id,claim_date,quantity,link,api_order_id,status)
            VALUES(?,?,?,?,?,?,?)""", (uid, sid, today, qty, link, api_id, status))
        conn.commit()
        conn.close()

    #  الأدمنية 
    @classmethod
    def get_extra_admins(cls):
        conn = cls.get_conn()
        r = conn.execute("SELECT * FROM extra_admins").fetchall()
        conn.close()
        return r

    @classmethod
    def add_extra_admin(cls, tg_id, full_name=""):
        conn = cls.get_conn()
        try:
            conn.execute("INSERT INTO extra_admins(tg_id,full_name) VALUES(?,?)", (tg_id, full_name))
            conn.commit()
            conn.close()
            return True
        except:
            conn.close()
            return False

    @classmethod
    def remove_extra_admin(cls, tg_id):
        conn = cls.get_conn()
        conn.execute("DELETE FROM extra_admins WHERE tg_id=?", (tg_id,))
        conn.commit()
        conn.close()

    #  تصدير/استيراد قاعدة البيانات 
    @classmethod
    def export_db_json(cls):
        """تصدير إعدادات قاعدة البيانات كـ JSON"""
        conn = cls.get_conn()
        data = {}

        tables = ["config", "smm_sites", "apps", "app_services",
                  "free_services", "wheel_prizes", "mandatory_channels",
                  "points_channels", "order_channels", "invite_links"]

        for table in tables:
            try:
                rows = conn.execute(f"SELECT * FROM {table}").fetchall()
                data[table] = [dict(r) for r in rows]
            except:
                data[table] = []

        conn.close()
        return json.dumps(data, ensure_ascii=False, indent=2)

    @classmethod
    def import_db_json(cls, json_str):
        """استيراد إعدادات قاعدة البيانات من JSON"""
        try:
            data = json.loads(json_str)
            conn = cls.get_conn()
            c = conn.cursor()

            # استيراد الإعدادات
            if "config" in data:
                for row in data["config"]:
                    c.execute("INSERT OR REPLACE INTO config(key,value) VALUES(?,?)",
                              (row["key"], row["value"]))

            # استيراد مواقع SMM
            if "smm_sites" in data:
                c.execute("DELETE FROM smm_sites")
                for row in data["smm_sites"]:
                    c.execute("""INSERT OR IGNORE INTO smm_sites(name,api_url,api_key,is_active,is_default)
                        VALUES(?,?,?,?,?)""",
                        (row.get("name",""), row.get("api_url",""), row.get("api_key",""),
                         row.get("is_active",1), row.get("is_default",0)))

            # استيراد الأقسام
            if "apps" in data:
                c.execute("DELETE FROM apps")
                for row in data["apps"]:
                    try:
                        c.execute("INSERT OR IGNORE INTO apps(id,name,emoji,is_active,sort_order) VALUES(?,?,?,?,?)",
                                  (row.get("id"), row.get("name",""), row.get("emoji",""),
                                   row.get("is_active",1), row.get("sort_order",0)))
                    except:
                        c.execute("INSERT OR IGNORE INTO apps(id,name,is_active,sort_order) VALUES(?,?,?,?)",
                                  (row.get("id"), row.get("name",""),
                                   row.get("is_active",1), row.get("sort_order",0)))

            # استيراد الخدمات
            if "app_services" in data:
                c.execute("DELETE FROM app_services")
                for row in data["app_services"]:
                    c.execute("""INSERT OR IGNORE INTO app_services
                        (id,app_id,name,emoji,api_service_id,site_id,points_per_1000,min_qty,max_qty,rate_per_1000,is_active)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                        (row.get("id"), row.get("app_id"), row.get("name",""),
                         row.get("emoji",""), row.get("api_service_id",""),
                         row.get("site_id"), row.get("points_per_1000",10),
                         row.get("min_qty",100), row.get("max_qty",100000),
                         row.get("rate_per_1000",0.5), row.get("is_active",1)))

            # استيراد جوائز العجلة
            if "wheel_prizes" in data:
                c.execute("DELETE FROM wheel_prizes")
                for row in data["wheel_prizes"]:
                    c.execute("INSERT INTO wheel_prizes(points,weight,emoji,label,is_active) VALUES(?,?,?,?,?)",
                              (row.get("points",10), row.get("weight",10),
                               row.get("emoji",""), row.get("label",""), row.get("is_active",1)))

            # استيراد الخدمات المجانية
            if "free_services" in data:
                for row in data["free_services"]:
                    c.execute("""INSERT OR IGNORE INTO free_services
                        (name,description,api_service_id,site_id,daily_limit,min_qty,max_qty,is_active)
                        VALUES(?,?,?,?,?,?,?,?)""",
                        (row.get("name",""), row.get("description",""),
                         row.get("api_service_id",""), row.get("site_id"),
                         row.get("daily_limit",1), row.get("min_qty",100),
                         row.get("max_qty",1000), row.get("is_active",1)))

            # استيراد القنوات الإجبارية
            if "mandatory_channels" in data:
                for row in data["mandatory_channels"]:
                    c.execute("""INSERT OR IGNORE INTO mandatory_channels
                        (channel_id,channel_name,channel_url,target_members) VALUES(?,?,?,?)""",
                        (row.get("channel_id",""), row.get("channel_name",""),
                         row.get("channel_url",""), row.get("target_members",0)))

            # استيراد قنوات النقاط
            if "points_channels" in data:
                for row in data["points_channels"]:
                    try:
                        c.execute("""INSERT OR IGNORE INTO points_channels
                            (channel_id,channel_name,channel_url,points_reward) VALUES(?,?,?,?)""",
                            (row.get("channel_id",""), row.get("channel_name",""),
                             row.get("channel_url",""), row.get("points_reward",20)))
                    except:
                        pass

            # استيراد قنوات الطلبات
            if "order_channels" in data:
                for row in data["order_channels"]:
                    try:
                        c.execute("""INSERT OR IGNORE INTO order_channels
                            (channel_id,channel_name) VALUES(?,?)""",
                            (row.get("channel_id",""), row.get("channel_name","")))
                    except:
                        pass

            # استيراد روابط الدعوة
            if "invite_links" in data:
                for row in data["invite_links"]:
                    try:
                        c.execute("""INSERT OR IGNORE INTO invite_links
                            (code,points_reward,max_uses,is_active) VALUES(?,?,?,?)""",
                            (row.get("code",""), row.get("points_reward",0),
                             row.get("max_uses",0), row.get("is_active",1)))
                    except:
                        pass

            conn.commit()
            conn.close()
            return True, "تم الاستيراد بنجاح! (متوافق مع جميع الإصدارات)"
        except Exception as e:
            try:
                conn.close()
            except:
                pass
            return False, f"خطأ في الاستيراد: {e}"

# ==========================================
#   3. SMMParty API
# ==========================================
class smm:
    STATUS_MAP = {
        "Pending": "⏳ قيد الانتظار", "In progress": " قيد التنفيذ",
        "Completed": " مكتمل", "Partial": " مكتمل جزئياً",
        "Canceled": " ملغي", "Processing": " جاري المعالجة",
    }

    @classmethod
    def _post(cls, action, **params):
        data = {"key": config.SMMPARTY_API_KEY, "action": action, **params}
        try:
            resp = requests.post(config.SMMPARTY_API_URL, data=data, timeout=15)
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    @classmethod
    def get_balance(cls):
        try: return float(cls._post("balance").get("balance", 0))
        except Exception: return 0.0

    @classmethod
    def create_order(cls, service_id, link, quantity):
        return cls._post("add", service=service_id, link=link, quantity=quantity)

    @classmethod
    def get_order_status(cls, order_id):
        return cls._post("status", order=order_id)

    @classmethod
    def arabic_status(cls, status):
        return cls.STATUS_MAP.get(status, f" {status}")

    @classmethod
    def get_services_list(cls):
        """يجيب كل الخدمات من SMMParty (للتخزين المؤقت + البحث)"""
        try:
            data = {"key": config.SMMPARTY_API_KEY, "action": "services"}
            resp = requests.post(config.SMMPARTY_API_URL, data=data, timeout=20)
            return resp.json() or []
        except Exception:
            return []

    @classmethod
    def get_service_info(cls, service_id):
        """
        يبحث في خدمات SMMParty عن خدمة بالـ ID ويُرجع بياناتها كاملة:
        {service, name, type, category, rate, min, max, ...}
        أو None لو مش موجودة.
        """
        try:
            sid = str(service_id).strip()
            for s in cls.get_services_list():
                if str(s.get("service", "")).strip() == sid:
                    return s
        except Exception:
            pass
        return None

# ==========================================
#   3.5 رموز تعبيرية مميزة (Telegram Premium Emoji)
# ==========================================
def pe(emoji_char: str, custom_emoji_id: str = "") -> str:
    """
    يُرجع HTML يدعم Premium Emoji في تليجرام.
    لو فيه custom_emoji_id يستخدم <tg-emoji>، وإلا يرجع الإيموجي العادي.
    استخدمها مع parse_mode='HTML' فقط.
    """
    if custom_emoji_id:
        return f'<tg-emoji emoji-id="{custom_emoji_id}">{emoji_char}</tg-emoji>'
    return emoji_char

# ==========================================
#   4. الأزرار (Keyboards)
# ==========================================

class ColoredButton(InlineKeyboardButton):
    """زر ملوّن + دعم icon_custom_emoji_id (Premium Custom Emoji)"""
    def __init__(self, text, callback_data=None, url=None, style=None,
                 icon_custom_emoji_id=None, **kwargs):
        super().__init__(text=text, callback_data=callback_data, url=url, **kwargs)
        self._btn_style = style
        self._icon_custom_emoji_id = icon_custom_emoji_id

    def to_dict(self):
        d = super().to_dict()
        if self._btn_style:
            d["style"] = self._btn_style
        if self._icon_custom_emoji_id:
            d["icon_custom_emoji_id"] = str(self._icon_custom_emoji_id)
        return d

    def to_json(self):
        import json
        return json.dumps(self.to_dict())

_STYLE_MAP = {"green": "success", "red": "danger", "blue": "primary"}

_BTN_EMOJI_CACHE = None

def _load_btn_emoji_cache():
    global _BTN_EMOJI_CACHE
    try:
        _BTN_EMOJI_CACHE = db.list_btn_emojis()
    except Exception:
        _BTN_EMOJI_CACHE = {}

def _invalidate_btn_emoji_cache():
    global _BTN_EMOJI_CACHE
    _BTN_EMOJI_CACHE = None

def _resolve_btn_emoji(cb):
    if not cb:
        return ""
    global _BTN_EMOJI_CACHE
    if _BTN_EMOJI_CACHE is None:
        _load_btn_emoji_cache()
    return _BTN_EMOJI_CACHE.get(cb, "") if _BTN_EMOJI_CACHE else ""

def _btn(text, cb=None, url=None, color="blue", emoji_id=None):
    """زر عام مع دعم ألوان وإيموجي مميز."""
    style = _STYLE_MAP.get(color, "primary")
    if emoji_id is None:
        emoji_id = _resolve_btn_emoji(cb)
    return ColoredButton(text=text, callback_data=cb, url=url, style=style,
                         icon_custom_emoji_id=(str(emoji_id) if emoji_id else None))

def mk(*rows):
    m = InlineKeyboardMarkup()
    for row in rows:
        m.row(*row)
    return m

class kb:
    @classmethod
    def _btn(cls, text, callback_data=None, url=None, style=None, emoji_id=None):
        """زر مع دعم ألوان وإيموجي مميز."""
        if emoji_id is None:
            emoji_id = _resolve_btn_emoji(callback_data)
        return ColoredButton(text=text, callback_data=callback_data, url=url,
                             style=style,
                             icon_custom_emoji_id=(str(emoji_id) if emoji_id else None))

    #  القائمة الرئيسية 
    @classmethod
    def main_menu(cls, updates_channel=None, bot_channel=None, support=None):
        m = InlineKeyboardMarkup(row_width=2)

        def lbl(key, default_text, default_emoji=""):
            return db.btn_label(key, default_text, default_emoji)

        def vis(key):
            return db.btn_visible(key)

        def clr(key, default="primary"):
            return db.btn_color(key, default)

        #  تمويل (زرار كبير فوق) 
        if vis("fund_start"):
            m.row(cls._btn(lbl("fund_start"," تمويل قناة / جروب",""), "fund_start", style=clr("fund_start","danger")))
        #  تجميع نقاط ولوحتي 
        row1 = []
        if vis("collect_section"):
            row1.append(cls._btn(lbl("collect_section"," تجميع نقاط",""), "collect_section", style=clr("collect_section","success")))
        if vis("my_account"):
            row1.append(cls._btn(lbl("my_account"," لوحتي",""), "my_account", style=clr("my_account","primary")))
        if row1: m.row(*row1)
        #  طلباتي ونقاطي 
        row2 = []
        if vis("my_orders"):
            row2.append(cls._btn(lbl("my_orders"," طلباتي",""), "my_orders", style=clr("my_orders","primary")))
        if vis("my_balance"):
            row2.append(cls._btn(lbl("my_balance"," نقاطي",""), "my_balance", style=clr("my_balance","success")))
        if row2: m.row(*row2)
        #  زر مكافأة 10 إحالات 
        m.row(cls._btn("🎁 200 نقطة هدية كل 24 ساعة", "ten_member_gift", style="success"))
        #  شحن وتحويل 
        row3 = []
        if vis("charge_menu"):
            row3.append(cls._btn(lbl("charge_menu"," شحن نقاط",""), "charge_menu", style=clr("charge_menu","success")))
        if vis("transfer_pts"):
            row3.append(cls._btn(lbl("transfer_pts"," تحويل نقاط",""), "transfer_pts", style=clr("transfer_pts","primary")))
        if row3: m.row(*row3)
        #  اشتراك إجباري 
        if vis("subscription_plans"):
            m.row(cls._btn(lbl("subscription_plans"," اشتراك إجباري",""), "subscription_plans", style=clr("subscription_plans","success")))
        #  ليدبورد 
        if vis("leaderboard"):
            m.row(cls._btn(lbl("leaderboard"," ليدبورد",""), "leaderboard", style=clr("leaderboard","primary")))
        #  كود هدية + قنوات البوت + دعم 
        row4 = []
        if vis("enter_invite_code"):
            row4.append(cls._btn(lbl("enter_invite_code"," كود هدية",""), "enter_invite_code", style=clr("enter_invite_code","success")))
        if bot_channel:
            row4.append(cls._btn(lbl("bot_channels"," قنوات البوت",""), "bot_channels", style=clr("bot_channels","primary")))
        if row4: m.row(*row4)
        if vis("support"):
            m.row(cls._btn(lbl("support"," الدعم الفني",""), "support", style=clr("support","danger")))
        #  زر تابع آخر التحديثات 
        if updates_channel and vis("updates_channel_menu"):
            m.row(cls._btn(lbl("updates_channel_menu"," تابع آخر التحديثات",""), url=updates_channel, style=clr("updates_channel_menu","primary")))
        #  تمويلات مكتملة 
        if vis("completed_fundings"):
            m.row(cls._btn(lbl("completed_fundings"," التمويلات المكتملة",""), "completed_fundings", style=clr("completed_fundings","success")))
        return m

    #  قسم تجميع النقاط 
    @classmethod
    def collect_section_menu(cls):
        m = InlineKeyboardMarkup(row_width=2)
        m.row(cls._btn("🎡 عجلة الحظ", "wheel_open", style="success"))
        m.row(
            cls._btn("🎁 الهدية اليومية", "daily_gift", style="success"),
            cls._btn("🎀 الهدية الأسبوعية", "weekly_gift", style="success"),
        )
        m.row(cls._btn("📣 الاشتراك بالقنوات", "points_channels", style="primary"))
        m.row(cls._btn("👥 دعوة صديق (إحالة)", "referral", style="primary"))
        m.row(cls._btn("🎁 مكافأة 10 إحالات (200 نقطة)", "ten_member_gift", style="success"))
        m.row(cls._btn("🔙 رجوع للقائمة", "back_main", style="danger"))
        return m

    @classmethod
    def wheel_keyboard(cls):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("🎡 لف العجلة الآن!", "wheel_spin", style="success"))
        m.row(cls._btn("🔙 رجوع", "collect_section", style="danger"))
        return m

    #  خدماتي (الأقسام/الأبليكيشنز) 
    @classmethod
    def services_apps_keyboard(cls, apps):
        m = InlineKeyboardMarkup(row_width=2)
        if not apps:
            m.row(cls._btn("رجوع للقائمة", "back_main", style="danger"))
            return m
        row = []
        for a in apps:
            row.append(cls._btn(f"{a['emoji']} {a['name']}", f"app_{a['id']}", style="primary"))
            if len(row) == 2:
                m.row(*row); row = []
        if row: m.row(*row)
        m.row(cls._btn("رجوع للقائمة", "back_main", style="danger"))
        return m

    @classmethod
    def app_services_keyboard(cls, app_id, services):
        m = InlineKeyboardMarkup()
        for s in services:
            m.row(cls._btn(
                f"{s['emoji']} {s['name']}  {s['points_per_unit']} نقطة/وحدة",
                f"svc_{s['id']}", style="primary"))
        m.row(cls._btn("رجوع للأقسام", "my_services", style="danger"))
        return m

    @classmethod
    def fund_type_keyboard(cls):
        m = InlineKeyboardMarkup()
        m.row(
            cls._btn("📢 قناة تليجرام", "fund_channel", style="primary"),
            cls._btn("👥 جروب تليجرام", "fund_group", style="primary"),
        )
        m.row(cls._btn("🔙 رجوع للقائمة", "back_main", style="danger"))
        return m

    @classmethod
    def confirm_order_keyboard(cls):
        m = InlineKeyboardMarkup()
        m.row(
            cls._btn("✅ تأكيد وإرسال", "order_confirm", style="success"),
            cls._btn("❌ إلغاء", "back_main", style="danger"),
        )
        return m

    @classmethod
    def order_detail_keyboard(cls, order_id):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("تحديث الحالة", f"order_refresh_{order_id}", style="primary"))
        m.row(cls._btn("رجوع للطلبات", "my_orders", style="danger"))
        return m

    @classmethod
    def back_keyboard(cls, callback="back_main"):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("🔙 رجوع", callback, style="danger"))
        return m

    @classmethod
    def subscribe_keyboard(cls, channels, user_id):
        m = InlineKeyboardMarkup()
        for ch in channels:
            m.row(cls._btn(f" اشترك في {ch['channel_name']}", url=ch["channel_url"], style="primary"))
        m.row(cls._btn("تحققت من الاشتراك", f"check_sub_{user_id}", style="success"))
        return m

    @classmethod
    def points_channels_keyboard(cls, channels):
        m = InlineKeyboardMarkup()
        for ch in channels:
            m.row(cls._btn(f" {ch['channel_name']} (+{ch['points_reward']} نقطة)",
                           url=ch["channel_url"], style="success"))
        m.row(cls._btn("جمّعت نقاطي!", "collect_points", style="primary"))
        m.row(cls._btn("رجوع", "collect_section", style="danger"))
        return m

    @classmethod
    def orders_list_keyboard(cls, orders):
        m = InlineKeyboardMarkup()
        icons = {"pending": "⏳", "inprogress": "", "completed": "", "partial": "", "canceled": ""}
        for o in orders:
            ic = icons.get(o["status"].lower(), "")
            m.row(cls._btn(f" طلب #{o['id']} {ic}", f"order_detail_{o['id']}", style="primary"))
        m.row(cls._btn("رجوع", "back_main", style="danger"))
        return m

    @classmethod
    def admin_charge_settings_keyboard(cls):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("سعر النجوم (نجمة = كم نقطة)", "adm_set_stars_rate", style="success"))
        m.row(cls._btn("⭐ منشور استقبال النجوم", "adm_set_stars_post", style="success"))
        m.row(cls._btn("سعر الكاش ($ = كم نقطة)", "adm_set_cash_rate", style="primary"))
        m.row(cls._btn("سعر USDT (USDT = كم نقطة)", "adm_set_usdt_rate", style="primary"))
        m.row(cls._btn("رقم فودافون كاش", "adm_vodafone_number", style="success"))
        m.row(cls._btn("عرض إعدادات الشحن", "adm_view_charge_settings", style="primary"))
        m.row(cls._btn("رجوع للوحة", "adm_back", style="danger"))
        return m

    @classmethod
    def charge_menu_keyboard(cls):
        m = InlineKeyboardMarkup(row_width=2)
        m.row(cls._btn("⭐️ شحن بالنجوم (Stars)", "charge_stars", style="success"))
        m.row(cls._btn("💵 شحن بالكاش (يدوي)", "charge_cash", style="primary"))
        m.row(cls._btn("💎 شحن بـ USDT", "charge_usdt", style="success"))
        m.row(cls._btn("🤝 شحن عبر الوكيل", "charge_reseller", style="primary"))
        m.row(cls._btn("🔙 رجوع للقائمة", "back_main", style="danger"))
        return m

    @classmethod
    def fund_qty_keyboard(cls, max_can, pts_per_member, svc_min):
        m = InlineKeyboardMarkup(row_width=3)
        options = [10, 50, 100, 200, 500, 1000]
        valid = [o for o in options if o >= int(svc_min) and o <= max_can]
        row = []
        for o in valid:
            row.append(cls._btn(f"{o:,} ", f"fund_qty_{o}", style="primary"))
            if len(row) == 3:
                m.row(*row); row = []
        if row: m.row(*row)
        if max_can >= int(svc_min):
            m.row(cls._btn(f" تمويل كل نقاطك ({max_can:,} عضو)", f"fund_qty_{max_can}", style="success"))
        m.row(cls._btn("رجوع", "back_main", style="danger"))
        return m

    @classmethod
    def stars_amounts_keyboard(cls):
        m = InlineKeyboardMarkup(row_width=3)
        amounts = [1, 5, 10, 20, 50, 70, 100, 300, 1000]
        row = []
        for a in amounts:
            row.append(cls._btn(f"⭐ {a}", f"stars_buy_{a}", style="success"))
            if len(row) == 3:
                m.row(*row); row = []
        if row: m.row(*row)
        m.row(cls._btn("رجوع", "charge_menu", style="danger"))
        return m

    @classmethod
    def shop_keyboard(cls, items):
        m = InlineKeyboardMarkup()
        for it in items:
            stock_txt = f" | مخزون: {it['stock']}" if it['stock'] >= 0 else ""
            m.row(cls._btn(
                f"{it['emoji']} {it['name']}  {it['price']:,} نقطة{stock_txt}",
                f"shop_buy_{it['id']}", style="success"))
        m.row(cls._btn("رجوع للقائمة", "back_main", style="danger"))
        return m

    @classmethod
    def leaderboard_keyboard(cls):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("تحديث", "leaderboard", style="primary"))
        m.row(cls._btn("رجوع", "back_main", style="danger"))
        return m

    @classmethod
    def completed_fundings_keyboard(cls, fundings):
        m = InlineKeyboardMarkup()
        for f in fundings:
            url = f.get("channel_url") or ""
            if url:
                m.row(cls._btn(f"{f['emoji']} {f['title']}  {f['members']:,} عضو", url=url, style="success"))
            else:
                m.row(cls._btn(f"{f['emoji']} {f['title']}  {f['members']:,} عضو", f"funding_detail_{f['id']}", style="success"))
        m.row(cls._btn("رجوع", "back_main", style="danger"))
        return m

    @classmethod
    def admin_fundings_keyboard(cls, fundings):
        m = InlineKeyboardMarkup()
        for f in fundings:
            st = "" if f["is_active"] else ""
            m.row(
                cls._btn(f"{st} {f['emoji']} {f['title']}", f"adm_funding_tog_{f['id']}", style="primary"),
                cls._btn("", f"adm_funding_del_{f['id']}", style="danger"),
            )
        m.row(cls._btn("إضافة تمويل مكتمل", "adm_funding_add", style="success"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_charge_requests_keyboard(cls, requests):
        m = InlineKeyboardMarkup()
        for r in requests[:10]:
            method_icons = {"stars": "", "cash": "", "reseller": ""}
            ic = method_icons.get(r["method"], "")
            m.row(
                cls._btn(f" #{r['id']} {ic}{r['amount']}نق", f"adm_charge_ok_{r['id']}", style="success"),
                cls._btn(f" رفض", f"adm_charge_rej_{r['id']}", style="danger"),
            )
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_shop_keyboard(cls, items):
        m = InlineKeyboardMarkup()
        for it in items:
            m.row(cls._btn(f" {it['emoji']} {it['name']} ({it['price']}نق)",
                           f"adm_shop_del_{it['id']}", style="danger"))
        m.row(cls._btn("إضافة منتج", "adm_shop_add", style="success"))
        m.row(cls._btn("طلبات المتجر", "adm_shop_orders", style="primary"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_resellers_keyboard(cls, resellers):
        m = InlineKeyboardMarkup()
        for r in resellers:
            name = r["full_name"] or str(r["tg_id"])
            m.row(cls._btn(f" {name}  {r['discount']}% خصم",
                           f"adm_res_del_{r['tg_id']}", style="danger"))
        m.row(cls._btn("إضافة وكيل", "adm_res_add", style="success"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    #  لوحة الأدمن 
    @classmethod
    def admin_main_keyboard(cls):
        m = InlineKeyboardMarkup(row_width=2)

        #   إحصائيات ومستخدمون 
        m.row(
            cls._btn("الإحصائيات", "adm_stats", style="primary"),
            cls._btn("المستخدمون", "adm_users", style="primary"),
        )

        #   الخدمات والأقسام 
        m.row(cls._btn("إدارة الأقسام والخدمات", "adm_apps", style="success"))

        #   القنوات 
        m.row(
            cls._btn("قنوات إجبارية", "adm_mandatory", style="primary"),
            cls._btn("قنوات النقاط", "adm_points_ch", style="success"),
        )
        m.row(
            cls._btn("قناة التمويلات", "adm_orders_ch", style="primary"),
            cls._btn("قناة التحديثات", "adm_updates_ch", style="primary"),
        )
        m.row(cls._btn("قناة البوت الرئيسية", "adm_bot_channel", style="primary"))

        #   الشحن والمالية 
        m.row(
            cls._btn("طلبات الشحن", "adm_charges", style="success"),
            cls._btn("شحن نقاط", "adm_topup", style="success"),
        )
        m.row(cls._btn("إعدادات الشحن", "adm_charge_settings", style="primary"))

        #   التمويلات والإحالات 
        m.row(
            cls._btn("التمويلات المكتملة", "adm_fundings", style="success"),
            cls._btn("سجل الإحالات", "adm_referral_log", style="primary"),
        )

        #   الإعدادات 
        m.row(
            cls._btn("إعدادات الخدمة", "adm_service", style="primary"),
            cls._btn("إعدادات النقاط", "adm_points_settings", style="primary"),
        )
        m.row(
            cls._btn("عجلة الحظ", "adm_wheel", style="success"),
            cls._btn("روابط الهدايا", "adm_gift_links", style="success"),
        )

        #   تواصل 
        m.row(
            cls._btn("إذاعة جماعية", "adm_broadcast", style="primary"),
            cls._btn("يوزر الدعم", "adm_support", style="primary"),
        )

        #   الاشتراك الإجباري والأزرار 
        m.row(
            cls._btn("خطط الاشتراك", "adm_subscriptions", style="success"),
            cls._btn("تسميات الأزرار", "adm_button_labels", style="primary"),
        )

        #  إغلاق 
        m.row(
            cls._btn("إدارة الأدمنية", "adm_manage_admins", style="primary"),
            cls._btn("قاعدة البيانات", "db_main", style="danger"),
        )
        #  تشغيل / إيقاف البوت 
        bot_active = db.get_config("bot_active", "1")
        if bot_active == "1":
            m.row(cls._btn("🔴 إيقاف البوت مؤقتاً", "adm_bot_toggle", style="danger"))
        else:
            m.row(cls._btn("🟢 تشغيل البوت", "adm_bot_toggle", style="success"))
        m.row(cls._btn("إغلاق اللوحة", "adm_close", style="danger"))
        return m

    @classmethod
    def admin_apps_keyboard(cls, apps):
        m = InlineKeyboardMarkup()
        for a in apps:
            m.row(cls._btn(f"{a['emoji']} {a['name']}", f"adm_app_{a['id']}", style="primary"))
        m.row(cls._btn("إضافة قسم جديد", "adm_add_app", style="success"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_app_view_keyboard(cls, app_id, services):
        m = InlineKeyboardMarkup()
        for s in services:
            m.row(cls._btn(f"{s['emoji']} {s['name']} | {s['points_per_unit']} نقطة",
                           f"adm_svc_{s['id']}", style="primary"))
        m.row(cls._btn("إضافة خدمة لهذا القسم", f"adm_add_svc_{app_id}", style="success"))
        m.row(cls._btn("حذف هذا القسم", f"adm_del_app_{app_id}", style="danger"))
        m.row(cls._btn("رجوع", "adm_apps", style="danger"))
        return m

    @classmethod
    def admin_service_view_keyboard(cls, svc_id, app_id):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("حذف الخدمة", f"adm_del_svc_{svc_id}", style="danger"))
        m.row(cls._btn("رجوع للقسم", f"adm_app_{app_id}", style="danger"))
        return m

    @classmethod
    def admin_service_keyboard(cls):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("تغيير Service ID", "adm_set_service_id", style="primary"))
        m.row(cls._btn("تغيير السعر (نقاط/عضو)", "adm_set_price", style="success"))
        m.row(cls._btn("تغيير الحد الأدنى للتمويل", "adm_set_min_qty", style="primary"))
        m.row(cls._btn("عرض إعدادات الخدمة", "adm_view_service", style="primary"))
        m.row(cls._btn("رجوع للوحة", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_points_settings_keyboard(cls):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("نقاط الهدية اليومية", "adm_set_daily_pts", style="primary"))
        m.row(cls._btn("نقاط الهدية الأسبوعية", "adm_set_weekly_pts", style="primary"))
        m.row(cls._btn("نقاط الإحالة", "adm_set_ref_pts", style="success"))
        m.row(cls._btn("سعر العضو (نقاط/عضو)", "adm_set_member_price", style="primary"))
        m.row(cls._btn("رجوع للوحة", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_mandatory_keyboard(cls, channels):
        m = InlineKeyboardMarkup()
        for ch in channels:
            target = ch["target_members"] if "target_members" in ch.keys() else 0
            current = ch["current_members"] if "current_members" in ch.keys() else 0
            label = f" {ch['channel_name']}"
            if target > 0:
                label += f" ({current}/{target})"
            m.row(cls._btn(label, f"adm_del_mand_{ch['channel_id']}", style="danger"))
        m.row(cls._btn("إضافة قناة (مساعد سهل)", "adm_add_mand", style="success"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_points_channels_keyboard(cls, channels):
        m = InlineKeyboardMarkup()
        for ch in channels:
            m.row(cls._btn(f" {ch['channel_name']} (+{ch['points_reward']})",
                           f"adm_del_ptch_{ch['channel_id']}", style="danger"))
        m.row(cls._btn("إضافة قناة نقاط", "adm_add_ptch", style="success"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_users_keyboard(cls):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("بحث عن مستخدم", "adm_search_user", style="primary"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_user_keyboard(cls, target_id, banned):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("إضافة نقاط", f"adm_add_pts_{target_id}", style="success"),
              cls._btn("خصم نقاط", f"adm_sub_pts_{target_id}", style="danger"))
        m.row(cls._btn("فك الحظر" if banned else " حظر",
                       f"adm_{'unban' if banned else 'ban'}_{target_id}",
                       style="success" if banned else "danger"))
        m.row(cls._btn("رجوع", "adm_users", style="danger"))
        return m

    @classmethod
    def admin_manage_admins_keyboard(cls, admins):
        m = InlineKeyboardMarkup()
        for a in admins:
            name = a["full_name"] or a["username"] or str(a["tg_id"])
            m.row(cls._btn(f" {name} ({a['tg_id']})", f"adm_del_admin_{a['tg_id']}", style="danger"))
        m.row(cls._btn("إضافة أدمن جديد", "adm_add_admin", style="success"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_invite_links_keyboard(cls, links):
        m = InlineKeyboardMarkup()
        for l in links[:10]:
            label = f" {l['code']} (+{l['points_reward']})  {l['current_uses']}/{l['max_uses'] or '∞'}"
            m.row(cls._btn(label, f"adm_del_invite_{l['code']}", style="danger"))
        m.row(cls._btn("إنشاء كود جديد", "adm_create_invite", style="success"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    # 
    #   أزرار الاشتراك الإجباري
    # 
    @classmethod
    def subscription_plans_keyboard(cls, plans, user_sub=None):
        m = InlineKeyboardMarkup()
        for p in plans:
            prices = []
            if p["price_stars"] > 0: prices.append(f"{p['price_stars']}")
            if p["price_vodafone"] > 0: prices.append(f"{p['price_vodafone']} ج")
            if p["price_usdt"] > 0: prices.append(f"{p['price_usdt']}$")
            price_str = " | ".join(prices) if prices else "مجاني"
            m.row(cls._btn(
                f"{p['emoji']} {p['name']} ({p['duration_days']} يوم)  {price_str}",
                f"sub_plan_{p['id']}", style="success"))
        m.row(cls._btn("رجوع للقائمة", "back_main", style="danger"))
        return m

    @classmethod
    def subscription_payment_keyboard(cls, plan_id):
        m = InlineKeyboardMarkup()
        m.row(cls._btn("دفع بالنجوم", f"sub_pay_stars_{plan_id}", style="success"))
        m.row(cls._btn("دفع بفودافون كاش", f"sub_pay_vodafone_{plan_id}", style="primary"))
        m.row(cls._btn("دفع بـ USDT", f"sub_pay_usdt_{plan_id}", style="primary"))
        m.row(cls._btn("رجوع", "subscription_plans", style="danger"))
        return m

    @classmethod
    def admin_subscriptions_keyboard(cls, plans):
        m = InlineKeyboardMarkup()
        for p in plans:
            st = "" if p["is_active"] else ""
            m.row(
                cls._btn(f"{st} {p['emoji']} {p['name']} ({p['duration_days']}يوم)",
                         f"adm_sub_tog_{p['id']}", style="primary"),
                cls._btn("", f"adm_sub_del_{p['id']}", style="danger"),
            )
        m.row(cls._btn("إضافة خطة", "adm_sub_add", style="success"))
        m.row(cls._btn("طلبات الاشتراك", "adm_sub_requests", style="primary"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_sub_requests_keyboard(cls, requests):
        m = InlineKeyboardMarkup()
        for r in requests[:10]:
            method_icons = {"stars": "", "vodafone": "", "usdt": ""}
            ic = method_icons.get(r["method"], "")
            m.row(
                cls._btn(f" #{r['id']} {ic} {r['plan_emoji']}{r['plan_name']}",
                         f"adm_sub_ok_{r['id']}", style="success"),
                cls._btn("رفض", f"adm_sub_rej_{r['id']}", style="danger"),
            )
        m.row(cls._btn("رجوع", "adm_subscriptions", style="danger"))
        return m

    # 
    #   أزرار إدارة تسميات الأزرار
    # 
    @classmethod
    def admin_button_colors_keyboard(cls, buttons):
        """لوحة تحكم ألوان الأزرار"""
        m = InlineKeyboardMarkup()
        color_emoji = {"primary": "", "success": "", "danger": ""}
        color_names = {"primary": "أزرق", "success": "أخضر", "danger": "أحمر"}
        for b in buttons:
            try:
                cur_color = b["btn_color"] or "primary"
            except Exception:
                cur_color = "primary"
            icon = color_emoji.get(cur_color, "")
            cname = color_names.get(cur_color, cur_color)
            m.row(cls._btn(
                f"{icon} {b['btn_emoji']} {b['btn_text']} ({cname})",
                f"adm_btn_color_{b['btn_key']}", style=cur_color
            ))
        m.row(cls._btn("رجوع لإدارة الأزرار", "adm_button_labels", style="danger"))
        return m

    @classmethod
    def admin_button_labels_keyboard(cls, buttons):
        m = InlineKeyboardMarkup()
        for b in buttons:
            vis = "" if b["is_visible"] else ""
            try:
                cur_color = b["btn_color"] or "primary"
            except Exception:
                cur_color = "primary"
            color_dot = {"primary": "", "success": "", "danger": ""}.get(cur_color, "")
            m.row(
                cls._btn(f"{vis} {color_dot} {b['btn_emoji']} {b['btn_text']}", f"adm_btn_edit_{b['btn_key']}", style="primary"),
                cls._btn("/", f"adm_btn_vis_{b['btn_key']}", style="primary"),
            )
        m.row(cls._btn("إدارة ألوان الأزرار", "adm_btn_colors", style="success"))
        m.row(cls._btn("إيموجي مميزة للأزرار", "adm_btn_emojis", style="success"))
        m.row(cls._btn("رجوع", "adm_back", style="danger"))
        return m

    @classmethod
    def admin_btn_color_keyboard(cls, btn_key, current_color):
        """اختيار لون زر معين"""
        m = InlineKeyboardMarkup()
        colors = [
            (" أزرق (primary)",  "primary"),
            (" أخضر (success)",  "success"),
            (" أحمر (danger)",   "danger"),
        ]
        for label, color in colors:
            marker = " " if color == current_color else ""
            m.row(cls._btn(f"{label}{marker}", f"adm_btn_setcolor_{btn_key}_{color}", style=color))
        m.row(cls._btn(" رجوع لألوان الأزرار", "adm_btn_colors", style="danger"))
        return m

    #  إيموجي مميزة للأزرار 
    @classmethod
    def admin_btn_emojis_main(cls, total_set=0):
        return mk(
            [_btn(f" عرض/تعديل ({total_set:,} مضبوط)", "adm_btn_emo_groups", color="blue")],
            [_btn(" مسح كل الرموز", "adm_btn_emo_clear_all", color="red")],
            [_btn(" مساعدة", "adm_btn_emo_help", color="blue")],
            [_btn("رجوع", "adm_back", color="blue")],
        )

    @classmethod
    def admin_btn_emojis_groups(cls):
        rows = []
        for i, (group_name, _items) in enumerate(STATIC_BUTTON_REGISTRY):
            rows.append([_btn(group_name, f"adm_btn_emo_g_{i}_0", color="blue")])
        rows.append([_btn("رجوع", "adm_btn_emojis", color="blue")])
        return mk(*rows)

    @classmethod
    def admin_btn_emojis_group(cls, group_idx, page=0, per_page=8):
        if group_idx < 0 or group_idx >= len(STATIC_BUTTON_REGISTRY):
            return cls.admin_btn_emojis_groups()
        _name, items = STATIC_BUTTON_REGISTRY[group_idx]
        emojis_set = db.list_btn_emojis()
        start = page * per_page
        end = start + per_page
        sub = items[start:end]
        rows = []
        for cb, label in sub:
            mark = "" if emojis_set.get(cb) else ""
            rows.append([_btn(f"{mark} {label}", f"adm_btn_emo_e:{cb}",
                              color="green" if emojis_set.get(cb) else "blue")])
        nav = []
        if page > 0:
            nav.append(_btn(" السابق", f"adm_btn_emo_g_{group_idx}_{page-1}", color="blue"))
        if end < len(items):
            nav.append(_btn("التالي ", f"adm_btn_emo_g_{group_idx}_{page+1}", color="blue"))
        if nav:
            rows.append(nav)
        rows.append([_btn("رجوع للأقسام", "adm_btn_emo_groups", color="blue")])
        return mk(*rows)

    @classmethod
    def admin_btn_emoji_edit(cls, cb, back_cb="adm_btn_emo_groups"):
        cur = db.get_btn_emoji(cb)
        rows = []
        if cur:
            rows.append([_btn(" حذف الرمز الحالي", f"adm_btn_emo_clr:{cb}", color="red")])
        rows.append([_btn(" ضبط/تغيير الرمز", f"adm_btn_emo_set:{cb}", color="green")])
        rows.append([_btn("رجوع", back_cb, color="blue")])
        return mk(*rows)

    @classmethod
    def back(cls, cb="adm_back"):
        return mk([_btn("رجوع", cb, color="blue")])

# 
#   سجل الأزرار الثابتة (إيموجي مميزة)
# 
STATIC_BUTTON_REGISTRY = [
    ("القائمة الرئيسية", [
        ("fund_start",            "تمويل قناة / جروب"),
        ("collect_section",       "تجميع نقاط"),
        ("my_account",            "لوحتي"),
        ("my_orders",             "طلباتي"),
        ("my_balance",            "نقاطي"),
        ("charge_menu",           "شحن نقاط"),
        ("transfer_pts",          "تحويل نقاط"),
        ("subscription_plans",    "اشتراك إجباري"),
        ("leaderboard",           "ليدبورد"),
        ("enter_invite_code",     "كود هدية"),
        ("bot_channels",          "قنوات البوت"),
        ("support",               "الدعم الفني"),
        ("updates_channel_menu",  "تابع آخر التحديثات"),
        ("completed_fundings",    "التمويلات المكتملة"),
        ("back_main",             "رجوع للقائمة"),
    ]),
    ("تجميع النقاط", [
        ("wheel_open",         " عجلة الحظ"),
        ("wheel_spin",         " لف العجلة"),
        ("daily_gift",         " الهدية اليومية"),
        ("weekly_gift",        " الهدية الأسبوعية"),
        ("points_channels",    " الاشتراك بالقنوات"),
        ("referral",           " دعوة صديق"),
    ]),
    ("لوحة الأدمن", [
        ("adm_apps",           " إدارة الأقسام"),
        ("adm_mandatory",      " قنوات إجبارية"),
        ("adm_points_ch",      " قنوات النقاط"),
        ("adm_stats",          " الإحصائيات"),
        ("adm_users",          " المستخدمين"),
        ("adm_broadcast",      " إذاعة"),
        ("adm_topup",          " شحن نقاط"),
        ("adm_wheel",          " عجلة الحظ (أدمن)"),
        ("adm_btn_emojis",     " إيموجي الأزرار"),
        ("adm_back",           " رجوع للأدمن"),
    ]),
]

def _label_for_cb(cb):
    for _grp, items in STATIC_BUTTON_REGISTRY:
        for k, lbl in items:
            if k == cb:
                return lbl
    return cb

# ==========================================
#   5. تشغيل البوت
# ==========================================
bot = telebot.TeleBot(config.BOT_TOKEN, parse_mode="HTML")
db.init_db()

# state in-memory
USER_STATE = {}

def get_state(tg_id):
    return USER_STATE.get(tg_id, {"state": None, "data": {}})

def set_state(tg_id, state, **data):
    USER_STATE[tg_id] = {"state": state, "data": data}

def clear_state(tg_id):
    USER_STATE.pop(tg_id, None)

def is_admin(tg_id):
    return tg_id in config.ADMIN_IDS or db.is_dynamic_admin(tg_id)

def send(chat_id, text, markup=None, **kwargs):
    return bot.send_message(chat_id, text, reply_markup=markup, **kwargs)

def edit(call, text, markup=None):
    try:
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=markup)
    except Exception:
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

def sync_check_subscriptions(tg_id):
    """يتأكد من اشتراك المستخدم في كل القنوات الإجبارية + يسجّل الانضمام"""
    channels = db.get_mandatory_channels()
    missing = []
    for ch in channels:
        try:
            member = bot.get_chat_member(ch["channel_id"], tg_id)
            if member.status in ("left", "kicked"):
                missing.append(ch)
            else:
                db.record_mandatory_join(tg_id, ch["channel_id"])
        except Exception:
            missing.append(ch)
    return len(missing) == 0, missing

# ==========================================
#   دالة مساعدة لإرسال الإشعارات للأدمنية
# ==========================================
def _notify_admins(text: str):
    all_admins = list(config.ADMIN_IDS)
    try:
        dyn = db.get_dynamic_admins()
        all_admins += [a["tg_id"] for a in dyn if a["tg_id"] not in all_admins]
    except Exception:
        pass
    for adm_id in all_admins:
        try:
            bot.send_message(adm_id, text, parse_mode="HTML")
        except Exception:
            pass

# ==========================================
#   6. أوامر المستخدم
# ==========================================
@bot.message_handler(commands=["start"])
def cmd_start(msg: Message):
    args = msg.text.split(maxsplit=1)
    ref_code    = None
    invite_code = None
    gift_code   = None
    if len(args) > 1:
        param = args[1].strip()
        if param.startswith("gift_"):
            gift_code = param[5:]          # استخرج الكود بعد gift_
        elif param.startswith("invite_"):
            invite_code = param[7:]
        else:
            ref_code = param

    user, referred_by, is_new = db.get_or_create_user(
        msg.from_user.id, msg.from_user.username or "",
        msg.from_user.full_name or "", ref_code
    )

    # تحديث بيانات المستخدم دائماً
    if user:
        db.update_user(msg.from_user.id,
                       username=msg.from_user.username or "",
                       full_name=msg.from_user.full_name or "")

    # حالة المستخدم غير موجود (خطأ نادر)
    if not user:
        send(msg.chat.id, " حدث خطأ، حاول مرة أخرى.")
        return

    # التحقق من الحظر
    if user.get("is_banned"):
        send(msg.chat.id, " <b>تم حظرك من استخدام البوت.</b>")
        return

    # معالجة رابط الهدية
    if gift_code:
        ok, pts, err = db.claim_gift_link(msg.from_user.id, gift_code)
        if ok:
            send(msg.chat.id,
                f" <b>تهانينا! استلمت هديتك!</b>\n\n"
                f" حصلت على <b>{pts:,}</b> نقطة! ")
            # إشعار الأدمن
            _notify_admins(
                f"🎁 <b>شخص استخدم رابط هدية!</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>الاسم:</b> {msg.from_user.full_name}\n"
                f"🆔 <b>الآيدي:</b> <code>{msg.from_user.id}</code>\n"
                f"📛 <b>اليوزر:</b> @{msg.from_user.username or 'لا يوجد'}\n"
                f"🎁 <b>الكود:</b> <code>{gift_code}</code>\n"
                f"💰 <b>النقاط:</b> {pts:,}\n"
                f"📅 <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            send(msg.chat.id, f" {err}")

    if invite_code:
        ok, pts, err = db.claim_invite_code(msg.from_user.id, invite_code)
        if ok:
            send(msg.chat.id, f" <b>تم تفعيل كود الدعوة!</b>\n\n حصلت على <b>{pts}</b> نقطة!")

    ok, missing = sync_check_subscriptions(msg.from_user.id)
    if not ok:
        # ── إشعار أدمن حتى لو ما اشترك بعد (مستخدم جديد) ──
        if is_new:
            try:
                total_users = db.get_conn().execute('SELECT COUNT(*) FROM users').fetchone()[0]
            except Exception:
                total_users = "؟"
            _notify_admins(
                f"🆕 <b>مستخدم جديد انضم!</b>\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👤 <b>الاسم:</b> {msg.from_user.full_name}\n"
                f"🆔 <b>الآيدي:</b> <code>{msg.from_user.id}</code>\n"
                f"📛 <b>اليوزر:</b> @{msg.from_user.username or 'لا يوجد'}\n"
                f"🔗 <b>الإحالة:</b> {'✅ عبر رابط إحالة' if ref_code else '❌ مباشر'}\n"
                f"⏳ <b>الحالة:</b> ينتظر الاشتراك في القنوات\n"
                f"📅 <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"━━━━━━━━━━━━━━━\n"
                f"👥 <b>إجمالي المستخدمين:</b> {total_users:,}"
            )
        send(msg.chat.id,
            "⚠️ <b>للاستخدام يجب الاشتراك أولاً في القنوات التالية:</b>\n\nبعد الاشتراك اضغط ✅",
            kb.subscribe_keyboard(missing, msg.from_user.id))
        return

    user = db.get_user(msg.from_user.id)
    ref_count = db.get_referral_count(msg.from_user.id)
    updates_ch = db.get_config("updates_channel")

    #  إشعار دخول مستخدم جديد (اشترك في القنوات وأكمل التسجيل)
    if is_new:
        try:
            total_users = db.get_conn().execute('SELECT COUNT(*) FROM users').fetchone()[0]
        except Exception:
            total_users = "؟"
        notif_text = (
            f"🆕 <b>مستخدم جديد انضم!</b>\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>الاسم:</b> {msg.from_user.full_name}\n"
            f"🆔 <b>الآيدي:</b> <code>{msg.from_user.id}</code>\n"
            f"📛 <b>اليوزر:</b> @{msg.from_user.username or 'لا يوجد'}\n"
            f"🔗 <b>الإحالة:</b> {'✅ عبر رابط إحالة' if ref_code else '❌ مباشر'}\n"
            f"✅ <b>الحالة:</b> اشترك وأكمل التسجيل\n"
            f"📅 <b>التاريخ:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👥 <b>إجمالي المستخدمين:</b> {total_users:,}"
        )
        _notify_admins(notif_text)

    welcome = (
        f"<b>أهلاً بك يا {msg.from_user.first_name} في {config.BOT_NAME}!</b>\n\n"
        f"<b>لوحتك الشخصية</b>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"<b>المعرف:</b> <code>{msg.from_user.id}</code>\n"
        f"<b>نقاطك:</b> <b>{user['points']:,}</b> نقطة\n"
        f"<b>إحالاتك:</b> <b>{ref_count}</b>\n"
        f"<b>عضو منذ:</b> {user['join_date'][:10]}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"<b>اختر من القائمة لتبدأ:</b>"
    )
    try:
        send(msg.chat.id, welcome, kb.main_menu(updates_ch, db.get_config("bot_channel"), db.get_config("support_username", "@support")))
    except Exception as e:
        print(f"[cmd_start] send welcome error: {e}")
        try:
            send(msg.chat.id, f"<b>أهلاً بك في {config.BOT_NAME}!</b>\n\nنقاطك: <b>{user['points']:,}</b>",
                 kb.main_menu(updates_ch, None, None))
        except Exception as e2:
            print(f"[cmd_start] fallback send error: {e2}")

    # (إشعار المستخدم الجديد فقط — إشعار "العائد" أُزيل لأنه كان يغرق الأدمن بالرسائل)

# ─── إشعار حظر/إلغاء حظر البوت + اكتشاف القنوات تلقائياً ───
@bot.my_chat_member_handler()
def handle_bot_blocked(update):
    """يُفعَّل لما يحظر المستخدم البوت أو يلغي الحظر، أو لما يُضاف كأدمن لقناة."""
    try:
        old_status = update.old_chat_member.status
        new_status = update.new_chat_member.status
        chat = update.chat
        user = update.from_user

        # ─── البوت أُضيف كأدمن في قناة/جروب ───
        if new_status in ("administrator", "creator") and chat.type in ("channel", "supergroup", "group"):
            try:
                conn_ch = db.get_conn()
                conn_ch.execute("""
                    CREATE TABLE IF NOT EXISTS discovered_channels (
                        chat_id   TEXT PRIMARY KEY,
                        chat_title TEXT DEFAULT '',
                        chat_type  TEXT DEFAULT '',
                        added_at   TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                conn_ch.execute(
                    "INSERT OR IGNORE INTO discovered_channels(chat_id, chat_title, chat_type) VALUES(?,?,?)",
                    (str(chat.id), chat.title or "", chat.type)
                )
                conn_ch.commit()
                conn_ch.close()
            except Exception:
                pass
            return

        # ─── البوت أُزيل من قناة ───
        if new_status in ("kicked", "left") and chat.type in ("channel", "supergroup", "group"):
            try:
                conn_ch = db.get_conn()
                conn_ch.execute("DELETE FROM discovered_channels WHERE chat_id=?", (str(chat.id),))
                conn_ch.commit()
                conn_ch.close()
            except Exception:
                pass

        # حظر البوت: kicked أو left (في المحادثات الخاصة)
        if new_status in ("kicked", "left") and old_status not in ("kicked", "left") and chat.type == "private":
            action_text = "🚫 <b>مستخدم حظر البوت!</b>"
        # إلغاء الحظر / عودة للبوت
        elif new_status in ("member",) and old_status in ("kicked", "left") and chat.type == "private":
            action_text = "✅ <b>مستخدم أعاد البوت (رفع الحظر)</b>"
        else:
            return  # حدث آخر لا يعنينا

        try:
            conn_tmp = db.get_conn()
            total_users = conn_tmp.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            blocked_note = conn_tmp.execute(
                "SELECT COUNT(*) FROM users WHERE is_banned=1"
            ).fetchone()[0]
            conn_tmp.close()
        except Exception:
            total_users = "؟"
            blocked_note = "؟"

        # جلب توب 5 إحالات
        top5_text = ""
        try:
            top5 = db.get_top_referrers(5)
            if top5:
                top5_text = "\n🏆 <b>توب 5 إحالات:</b>\n"
                for i, tr in enumerate(top5, 1):
                    tr_name = (tr["full_name"] or tr["username"] or str(tr["tg_id"]))[:20]
                    tr_user = f"@{tr['username']}" if tr["username"] else f"<code>{tr['tg_id']}</code>"
                    top5_text += f"  {i}. {tr_name} {tr_user} — <b>{tr['ref_count']}</b> إحالة\n"
        except Exception:
            top5_text = ""

        notif = (
            f"{action_text}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👤 <b>الاسم:</b> {user.full_name}\n"
            f"🆔 <b>المعرف:</b> <code>{user.id}</code>\n"
            f"📛 <b>اليوزر:</b> @{user.username or 'لا يوجد'}\n"
            f"📅 <b>الوقت:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"━━━━━━━━━━━━━━━\n"
            f"👥 <b>إجمالي المستخدمين:</b> {total_users:,}\n"
            f"🚫 <b>المحظورون من البوت:</b> {blocked_note}"
            f"{top5_text}"
        )

        all_admins = list(config.ADMIN_IDS)
        try:
            dyn = db.get_dynamic_admins()
            all_admins += [a["tg_id"] for a in dyn if a["tg_id"] not in all_admins]
        except Exception:
            pass
        for adm_id in all_admins:
            try:
                bot.send_message(adm_id, notif, parse_mode="HTML")
            except Exception:
                pass
    except Exception as e:
        print(f"[handle_bot_blocked] error: {e}")

#  رجوع للقائمة 
@bot.callback_query_handler(func=lambda c: c.data == "back_main")
def cb_back_main(call: CallbackQuery):
    clear_state(call.from_user.id)
    user = db.get_user(call.from_user.id)
    ref_count = db.get_referral_count(call.from_user.id)
    updates_ch = db.get_config("updates_channel")
    welcome = (
        f" <b>{config.BOT_NAME}</b> \n\n"
        f"\n"
        f" <b>{call.from_user.first_name}</b>\n"
        f" نقاطك: <b>{user['points']:,}</b> |  إحالاتك: <b>{ref_count}</b>\n"
        f"\n\n"
        f" <b>اختر من القائمة:</b>"
    )
    edit(call, welcome, kb.main_menu(updates_ch, db.get_config("bot_channel"), db.get_config("support_username", "@support")))

#  نقاطي 
@bot.callback_query_handler(func=lambda c: c.data == "my_balance")
def cb_balance(call: CallbackQuery):
    user = db.get_user(call.from_user.id)
    pts_per_member = int(db.get_config("points_per_member", "1"))
    can_fund = user['points'] // pts_per_member if pts_per_member > 0 else 0
    edit(call,
        f" <b>نقاطي</b>\n\n"
        f"\n"
        f" النقاط: <b>{user['points']:,}</b> نقطة\n"
        f" يمكنك تمويل: <b>{can_fund:,}</b> عضو\n"
        f"\n\n"
        f"<i> اجمع المزيد من قسم  تجميع نقاط</i>",
        kb.back_keyboard())

# 
#   قسم تجميع النقاط
# 
@bot.callback_query_handler(func=lambda c: c.data == "collect_section")
def cb_collect_section(call: CallbackQuery):
    user = db.get_user(call.from_user.id)
    edit(call,
        f" <b>تجميع النقاط</b>\n\n"
        f"\n"
        f" رصيدك: <b>{user['points']:,}</b> نقطة\n"
        f"\n\n"
        f"اختر طريقة لجمع النقاط:\n"
        f" عجلة الحظ (10-1000 نقطة!)\n"
        f" الهدية اليومية\n"
        f" الهدية الأسبوعية\n"
        f" الاشتراك بالقنوات\n"
        f" دعوة صديق",
        kb.collect_section_menu())

#  الهدية اليومية 
@bot.callback_query_handler(func=lambda c: c.data == "daily_gift")
def cb_daily_gift(call: CallbackQuery):
    success, pts = db.claim_daily_gift(call.from_user.id)
    user = db.get_user(call.from_user.id)
    if success:
        edit(call,
            f" <b>الهدية اليومية</b>\n\n"
            f" حصلت على <b>{pts}</b> نقطة!\n"
            f" رصيدك الآن: <b>{user['points']:,}</b>\n\n"
            f"<i>عد غداً لهدية جديدة! ⏰</i>",
            kb.back_keyboard("collect_section"))
    else:
        edit(call,
            f" <b>الهدية اليومية</b>\n\n"
            f" حصلت على هديتك اليوم بالفعل!\n\n"
            f"<i>عد غداً ⏰</i>",
            kb.back_keyboard("collect_section"))

#  الهدية الأسبوعية 
@bot.callback_query_handler(func=lambda c: c.data == "weekly_gift")
def cb_weekly_gift(call: CallbackQuery):
    ok, pts, days_left = db.claim_weekly_gift(call.from_user.id)
    user = db.get_user(call.from_user.id)
    if ok:
        edit(call,
            f" <b>الهدية الأسبوعية</b>\n\n"
            f" حصلت على <b>{pts}</b> نقطة!\n"
            f" رصيدك: <b>{user['points']:,}</b>\n\n"
            f"<i>عد بعد 7 أيام لهدية جديدة </i>",
            kb.back_keyboard("collect_section"))
    else:
        edit(call,
            f" <b>الهدية الأسبوعية</b>\n\n"
            f"⏰ تبقى <b>{days_left}</b> يوم على هديتك القادمة.",
            kb.back_keyboard("collect_section"))


@bot.callback_query_handler(func=lambda c: c.data == "ten_member_gift")
def cb_ten_member_gift(call: CallbackQuery):
    from datetime import datetime
    tg_id = call.from_user.id
    conn = db.get_conn()
    u = conn.execute("SELECT last_ten_member_gift, points FROM users WHERE tg_id=?", (tg_id,)).fetchone()
    if not u:
        conn.close()
        bot.answer_callback_query(call.id, "❌ خطأ", show_alert=True)
        return
    now = datetime.now()
    last = u["last_ten_member_gift"] or ""
    if last:
        try:
            last_dt = datetime.fromisoformat(last)
            diff_hours = (now - last_dt).total_seconds() / 3600
            if diff_hours < 24:
                hours_left = round(24 - diff_hours, 1)
                conn.close()
                edit(call,
                    f"⏰ <b>مكافأة يومية</b>\n\n"
                    f"استلمت مكافأتك اليوم!\n"
                    f"تبقى <b>{hours_left}</b> ساعة على المكافأة القادمة.",
                    kb.back_keyboard())
                return
        except Exception:
            pass
    pts = 200
    conn.execute("UPDATE users SET points=points+?, last_ten_member_gift=? WHERE tg_id=?",
                 (pts, now.isoformat(), tg_id))
    conn.commit()
    new_pts = u["points"] + pts
    conn.close()
    edit(call,
        f"🎉 <b>مكافأة يومية!</b>\n\n"
        f"✅ حصلت على <b>{pts}</b> نقطة!\n"
        f"💰 رصيدك الآن: <b>{new_pts:,}</b>\n\n"
        f"<i>عد غداً لمكافأة جديدة ⏰</i>",
        kb.back_keyboard())

#  عجلة الحظ 
@bot.callback_query_handler(func=lambda c: c.data == "wheel_open")
def cb_wheel_open(call: CallbackQuery):
    can, hours_left = db.can_spin_wheel(call.from_user.id)
    user = db.get_user(call.from_user.id)
    if not can:
        edit(call,
            f" <b>عجلة الحظ</b>\n\n"
            f"⏰ تبقى <b>{hours_left}</b> ساعة على الدورة القادمة.\n"
            f" رصيدك: <b>{user['points']:,}</b>",
            kb.back_keyboard("collect_section"))
        return
    edit(call,
        f" <b>عجلة الحظ المحظوظة!</b>\n\n"
        f"\n"
        f" الجوائز: من <b>10</b> إلى <b>1000</b> نقطة!\n"
        f" كل ما زاد العدد، قلت فرصته \n"
        f"⏰ يمكنك اللعب كل 6 ساعات\n"
        f"\n\n"
        f" رصيدك: <b>{user['points']:,}</b> نقطة\n\n"
        f"اضغط الزر بالأسفل لتجربة حظك! ",
        kb.wheel_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "wheel_spin")
def cb_wheel_spin(call: CallbackQuery):
    can, hours_left = db.can_spin_wheel(call.from_user.id)
    if not can:
        bot.answer_callback_query(call.id, f"⏰ تبقى {hours_left} ساعة!", show_alert=True)
        return

    # جلب الجوائز من DB (يتحكم فيها الأدمن من اللوحة)
    prizes_rows = db.get_wheel_prizes(only_active=True)
    if not prizes_rows:
        bot.answer_callback_query(call.id, " لا توجد جوائز مُفعّلة حالياً", show_alert=True)
        return

    prizes = [(p["points"], float(p["weight"]), p["emoji"] or "") for p in prizes_rows]
    total = sum(w for _, w, _ in prizes)
    r = random.uniform(0, total)
    cum = 0.0
    won, won_emoji = prizes[0][0], prizes[0][2]
    for value, weight, em in prizes:
        cum += weight
        if r <= cum:
            won, won_emoji = value, em
            break

    db.add_points(call.from_user.id, won)
    db.mark_wheel_spin(call.from_user.id)
    user = db.get_user(call.from_user.id)

    bar = f"{won_emoji}  {won_emoji}"
    max_prize = max(p[0] for p in prizes)
    if won >= max_prize:        reaction = " جائزة كبرى!"
    elif won >= max_prize * 0.4: reaction = " جائزة ممتازة!"
    elif won >= max_prize * 0.1: reaction = " جائزة جيدة"
    else:                        reaction = " لا بأس، حاول لاحقاً"

    edit(call,
        f" <b>نتيجة عجلة الحظ</b>\n\n"
        f"{bar}\n\n"
        f" ربحت <b>{won}</b> نقطة! \n"
        f"{reaction}\n\n"
        f"\n"
        f" رصيدك الآن: <b>{user['points']:,}</b>\n"
        f"⏰ الدورة القادمة: بعد 6 ساعات",
        kb.back_keyboard("collect_section"))

#  حسابي / لوحتي 
@bot.callback_query_handler(func=lambda c: c.data == "my_account")
def cb_account(call: CallbackQuery):
    user = db.get_user(call.from_user.id)
    ref_count = db.get_referral_count(call.from_user.id)
    orders = db.get_user_orders(call.from_user.id, limit=100)
    completed = sum(1 for o in orders if o["status"].lower() == "completed")
    pending   = sum(1 for o in orders if o["status"].lower() in ("pending", "inprogress"))

    edit(call,
        f" <b>لوحتي الشخصية</b>\n\n"
        f"\n"
        f" المعرف: <code>{call.from_user.id}</code>\n"
        f" الاسم: <b>{call.from_user.full_name}</b>\n"
        f" يوزر: @{call.from_user.username or ''}\n"
        f"\n"
        f" النقاط: <b>{user['points']:,}</b>\n"
        f" الإحالات: <b>{ref_count}</b>\n"
        f"\n"
        f" إجمالي الطلبات: <b>{len(orders)}</b>\n"
        f" مكتملة: <b>{completed}</b>\n"
        f"⏳ قيد التنفيذ: <b>{pending}</b>\n"
        f"\n"
        f" تاريخ الانضمام: {user['join_date'][:10]}",
        kb.back_keyboard())

#  الإحالة 
@bot.callback_query_handler(func=lambda c: c.data == "referral")
def cb_referral(call: CallbackQuery):
    user = db.get_user(call.from_user.id)
    ref_count = db.get_referral_count(call.from_user.id)
    ref_pts = int(db.get_config("referral_points", str(config.REFERRAL_POINTS)))
    bot_username = config.BOT_USERNAME.lstrip("@")
    link = f"https://t.me/{bot_username}?start={user['referral_code']}"

    # توب 5 أكثر ناس عاملين إحالات
    top5_text = ""
    try:
        top5 = db.get_top_referrers(5)
        if top5:
            rank_emojis = {1: "🥇", 2: "🥈", 3: "🥉"}
            top5_text = "\n🏆 <b>توب 5 إحالات:</b>\n"
            for i, tr in enumerate(top5, 1):
                tr_name = (tr["full_name"] or tr["username"] or str(tr["tg_id"]))[:18]
                me_mark = " ← أنت" if tr["tg_id"] == call.from_user.id else ""
                rank_em = rank_emojis.get(i, f"{i}.")
                top5_text += f"  {rank_em} <b>{tr_name}</b> — {tr['ref_count']} إحالة{me_mark}\n"
    except Exception:
        top5_text = ""

    edit(call,
        f"👥 <b>دعوة صديق (الإحالة)</b>\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🔗 رابطك الخاص:\n<code>{link}</code>\n"
        f"━━━━━━━━━━━━━━━\n"
        f"🎁 المكافأة: <b>{ref_pts}</b> نقطة لكل صديق\n"
        f"📊 إحالاتك حتى الآن: <b>{ref_count}</b>\n\n"
        f"<i>شارك الرابط واجمع نقاط بلا حدود! 🚀</i>"
        f"{top5_text}",
        kb.back_keyboard("collect_section"))

#  طلباتي 
@bot.callback_query_handler(func=lambda c: c.data == "my_orders")
def cb_my_orders(call: CallbackQuery):
    orders = db.get_user_orders(call.from_user.id, limit=8)
    if not orders:
        edit(call, " <b>طلباتك</b>\n\n<i>لا توجد طلبات بعد.</i>", kb.back_keyboard())
        return
    icons = {"pending": "⏳", "inprogress": "", "completed": "", "partial": "", "canceled": ""}
    text = " <b>آخر طلباتك:</b>\n\n"
    for o in orders:
        ic = icons.get(o["status"].lower(), "")
        app = o["app_name"] if "app_name" in o.keys() and o["app_name"] else ""
        text += (f"{ic} <b>طلب #{o['id']}</b> {('| '+app) if app else ''}\n"
                 f"    الكمية: {o['quantity']:,} |  {o['points_used']:,} نقطة\n\n")
    edit(call, text, kb.orders_list_keyboard(orders))

@bot.callback_query_handler(func=lambda c: c.data.startswith("order_detail_"))
def cb_order_detail(call: CallbackQuery):
    order_id = int(call.data.split("_")[-1])
    order = db.get_order(order_id)
    if not order or order["user_id"] != call.from_user.id:
        bot.answer_callback_query(call.id, " الطلب غير موجود")
        return
    app = order["app_name"] if "app_name" in order.keys() and order["app_name"] else ""
    text = (
        f" <b>تفاصيل الطلب #{order['id']}</b>\n\n"
        f"\n"
        f" القسم: <b>{app}</b>\n"
        f" الخدمة: {order['service_name']}\n"
        f" رقم API: <code>{order['api_order_id'] or 'لا يوجد'}</code>\n"
        f" الرابط: <code>{order['link']}</code>\n"
        f" الكمية: {order['quantity']:,}\n"
        f" النقاط: {order['points_used']:,}\n"
        f" الحالة: {smm.arabic_status(order['status'].title())}\n"
        f" التاريخ: {order['created_at'][:16]}\n"
        f""
    )
    edit(call, text, kb.order_detail_keyboard(order_id))

@bot.callback_query_handler(func=lambda c: c.data.startswith("order_refresh_"))
def cb_order_refresh(call: CallbackQuery):
    order_id = int(call.data.split("_")[-1])
    order = db.get_order(order_id)
    if not order or not order["api_order_id"]:
        bot.answer_callback_query(call.id, " لا يوجد رقم API للطلب")
        return
    result = smm.get_order_status(order["api_order_id"])
    status = result.get("status", order["status"])
    db.update_order_status(order_id, status.lower())
    bot.answer_callback_query(call.id, f" الحالة: {smm.arabic_status(status)}")
    cb_order_detail(call)

@bot.callback_query_handler(func=lambda c: c.data == "support")
def cb_support(call: CallbackQuery):
    support = db.get_config("support_username", "@support")
    # تحويل اليوزر لرابط t.me
    username = support.lstrip("@")
    support_url = f"https://t.me/{username}"
    m = InlineKeyboardMarkup()
    m.row(kb._btn(f"🎧 {support}", url=support_url, style="success"))
    m.row(kb._btn("🔙 رجوع", "back_main", style="danger"))
    edit(call,
        f"🎧 <b>الدعم الفني</b>\n\n"
        f"\n"
        f"💬 للتواصل مع الدعم اضغط الزر أدناه\n"
        f"⏱ الرد خلال 24 ساعة\n"
        f"",
        m)

#
#   قنوات البوت
#
@bot.callback_query_handler(func=lambda c: c.data == "bot_channels")
def cb_bot_channels(call: CallbackQuery):
    """يعرض قائمة قنوات البوت - يدعم أكثر من قناة بفاصل |
    طريقة الإضافة في الإعدادات (bot_channel):
      https://t.me/ch1|اسم القناة 1|https://t.me/ch2|اسم القناة 2
    """
    raw = db.get_config("bot_channel", "")
    m = InlineKeyboardMarkup()
    if raw:
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        i = 0
        btn_num = 1
        while i < len(parts):
            url = parts[i]
            i += 1
            if i < len(parts) and not parts[i].startswith("http"):
                name = parts[i]
                i += 1
            else:
                name = f"قناة {btn_num}"
            m.row(kb._btn(f"📢 {name}", url=url, style="primary"))
            btn_num += 1
    else:
        m.row(kb._btn("📢 لا توجد قنوات مضافة بعد", callback_data="bot_channels", style="primary"))
    m.row(kb._btn("🔙 رجوع للقائمة", "back_main", style="danger"))
    edit(call,
        f"📢 <b>قنوات البوت</b>\n\n"
        f"اضغط على القناة للانضمام إليها 👇",
        m)

#
#   تابع آخر التحديثات
#
@bot.callback_query_handler(func=lambda c: c.data == "updates_channel_menu")
def cb_updates_channel_menu(call: CallbackQuery):
    """يعرض قائمة قنوات التحديثات - يدعم أكثر من قناة بفاصل |
    طريقة الإضافة في الإعدادات (updates_channel):
      https://t.me/ch1|اسم القناة 1|https://t.me/ch2|اسم القناة 2
    """
    raw = db.get_config("updates_channel", "")
    m = InlineKeyboardMarkup()
    if raw:
        parts = [p.strip() for p in raw.split("|") if p.strip()]
        i = 0
        btn_num = 1
        while i < len(parts):
            url = parts[i]
            i += 1
            if i < len(parts) and not parts[i].startswith("http"):
                name = parts[i]
                i += 1
            else:
                name = f"قناة {btn_num}"
            m.row(kb._btn(f"📡 {name}", url=url, style="primary"))
            btn_num += 1
    else:
        m.row(kb._btn("📡 لا توجد قنوات تحديثات مضافة", callback_data="updates_channel_menu", style="primary"))
    m.row(kb._btn("🔙 رجوع للقائمة", "back_main", style="danger"))
    edit(call,
        f"📡 <b>تابع آخر التحديثات</b>\n\n"
        f"اشترك في قنواتنا لتبقى على اطلاع بكل جديد 👇",
        m)

# 
#   ليدربورد
# 
RANK_EMOJIS = {1: "", 2: "", 3: ""}
TIER_EMOJI = [
    (50000, " ماسي",     ""),
    (20000, " بلاتيني",  ""),
    (10000, " ذهبي",     ""),
    (5000,  " فضي",      ""),
    (1000,  " برونزي",   ""),
    (0,     " مبتدئ",    ""),
]

def get_tier(points):
    for threshold, label, _ in TIER_EMOJI:
        if points >= threshold:
            return label
    return " مبتدئ"

def get_tier_icon(points):
    for threshold, _, icon in TIER_EMOJI:
        if points >= threshold:
            return icon
    return ""

@bot.callback_query_handler(func=lambda c: c.data == "leaderboard")
def cb_leaderboard(call: CallbackQuery):
    top = db.get_leaderboard(10)
    my_user = db.get_user(call.from_user.id)
    my_rank = ""
    # احسب رتبة المستخدم الحالي
    all_top = db.get_leaderboard(1000)
    for idx, u in enumerate(all_top, 1):
        if u["tg_id"] == call.from_user.id:
            my_rank = str(idx)
            break

    text = " <b>ليدبورد</b>\n\n"
    text += "\n"
    for i, u in enumerate(top, 1):
        rank_em = RANK_EMOJIS.get(i, f"<b>{i}</b>.")
        name = (u["full_name"] or u["username"] or str(u["tg_id"]))[:18]
        tier_icon = get_tier_icon(u["points"])
        me = "  أنت" if u["tg_id"] == call.from_user.id else ""
        separator = "" if i < len(top) else ""
        text += f"{separator} {rank_em} {tier_icon} <b>{name}</b>{me}\n"
        text += f"     <b>{u['points']:,}</b> نقطة\n"
    text += "\n"
    text += f" رتبتك: <b>#{my_rank}</b>  |  {get_tier(my_user['points'])}\n"
    text += f" نقاطك: <b>{my_user['points']:,}</b>"
    edit(call, text, kb.leaderboard_keyboard())

# 
#   التمويلات المكتملة
# 
@bot.callback_query_handler(func=lambda c: c.data == "completed_fundings")
def cb_completed_fundings(call: CallbackQuery):
    fundings = db.get_showcase_fundings(only_active=True)
    if not fundings:
        edit(call,
            " <b>التمويلات المكتملة</b>\n\n"
            "<i>لا توجد تمويلات مكتملة بعد.\n"
            "سيتم عرض إنجازاتنا هنا قريباً! </i>",
            kb.back_keyboard())
        return
    text = " <b>التمويلات المكتملة بنجاح</b>\n\n"
    text += f"\n"
    for i, f in enumerate(fundings, 1):
        sep = "" if i < len(fundings) else ""
        text += f"{sep} {f['emoji']} <b>{f['title']}</b>\n"
        text += f"    <b>{f['members']:,}</b> عضو\n"
        if f.get("description"):
            text += f"   <i>{f['description']}</i>\n"
    text += "\n"
    text += f" إجمالي: <b>{len(fundings)}</b> تمويل مكتمل "
    edit(call, text, kb.completed_fundings_keyboard(fundings))

@bot.callback_query_handler(func=lambda c: c.data.startswith("funding_detail_"))
def cb_funding_detail(call: CallbackQuery):
    fid = int(call.data.replace("funding_detail_", ""))
    conn = db.get_conn()
    f = conn.execute("SELECT * FROM completed_fundings WHERE id = ?", (fid,)).fetchone()
    conn.close()
    if not f:
        bot.answer_callback_query(call.id, " التمويل غير موجود"); return
    desc = f.get("description") or ""
    edit(call,
        f"{f['emoji']} <b>{f['title']}</b>\n\n"
        f"\n"
        f"  الأعضاء: <b>{f['members']:,}</b>\n"
        f"  التاريخ: {f['created_at'][:10]}\n"
        f"{'  ' + desc + chr(10) if desc else ''}"
        f"",
        kb.back_keyboard("completed_fundings"))

# 
#   شحن النقاط
# 
@bot.callback_query_handler(func=lambda c: c.data == "charge_menu")
def cb_charge_menu(call: CallbackQuery):
    stars_rate = db.get_config("stars_per_point", "1")
    cash_rate  = db.get_config("cash_rate", "1")
    usdt_rate  = db.get_config("usdt_rate", "1")
    edit(call,
        f" <b>شحن النقاط</b>\n\n"
        f"\n"
        f" نجوم تليجرام: <b>1 نجمة = {stars_rate} نقطة</b>\n"
        f" كاش: <b>1$ = {cash_rate} نقطة</b>\n"
        f" USDT: <b>1 USDT = {usdt_rate} نقطة</b>\n"
        f" عبر الوكيل: بأسعار خاصة\n"
        f"\n\n"
        f"اختر طريقة الشحن:",
        kb.charge_menu_keyboard())

#  شحن بالنجوم 
@bot.callback_query_handler(func=lambda c: c.data == "charge_stars")
def cb_charge_stars(call: CallbackQuery):
    stars_rate = int(db.get_config("stars_per_point", "1"))
    edit(call,
        f" <b>شحن بنجوم تليجرام</b>\n\n"
        f"\n"
        f"سعر الشحن: <b>1 نجمة = {stars_rate} نقطة</b>\n"
        f"\n\n"
        f"اختر الكمية:",
        kb.stars_amounts_keyboard())

@bot.callback_query_handler(func=lambda c: c.data.startswith("stars_buy_"))
def cb_stars_buy(call: CallbackQuery):
    stars = int(call.data.split("_")[-1])
    stars_rate = int(db.get_config("stars_per_point", "1"))
    pts = stars * stars_rate if stars_rate > 0 else stars
    if pts <= 0:
        bot.answer_callback_query(call.id, "❌ خطأ في إعداد سعر النجوم، تواصل مع الأدمن", show_alert=True)
        return
    prices = [telebot.types.LabeledPrice(label=f"⭐ {stars} نجمة = {pts:,} نقطة", amount=stars)]
    try:
        bot.send_invoice(
            call.message.chat.id,
            title=f"شحن {pts:,} نقطة",
            description=f"شحن {pts:,} نقطة عبر نجوم تليجرام ⭐",
            invoice_payload=f"stars_{call.from_user.id}_{pts}",
            provider_token="",
            currency="XTR",
            prices=prices,
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f"❌ خطأ: {e}", show_alert=True)

@bot.pre_checkout_query_handler(func=lambda q: True)
def pre_checkout(query):
    bot.answer_pre_checkout_query(query.id, ok=True)

@bot.message_handler(content_types=["successful_payment"])
def successful_payment(msg: Message):
    payload = msg.successful_payment.invoice_payload

    def _forward_stars_post(chat_id):
        post_link = db.get_config("stars_post_link", "")
        if not post_link:
            return
        try:
            link = post_link.rstrip("/")
            parts = link.split("/")
            if "/c/" in link:
                from_chat = int(f"-100{parts[-2]}")
                msg_id    = int(parts[-1])
            else:
                from_chat = f"@{parts[-2]}"
                msg_id    = int(parts[-1])
            bot.forward_message(chat_id, from_chat, msg_id)
        except Exception as e:
            print(f"[stars_post forward] {e}")

    if payload.startswith("stars_"):
        parts = payload.split("_")
        user_id = int(parts[1]); pts = int(parts[2])
        rid = db.create_charge_request(user_id, "stars", photo_id=str(pts), amount=pts)
        db.add_points(user_id, pts)
        db.update_charge_status(rid, "approved", "تم تلقائياً عبر النجوم")
        send(msg.chat.id,
            f" <b>تم الشحن بنجاح!</b>\n\n"
            f" تم إضافة <b>{pts:,}</b> نقطة لحسابك!\n"
            f" رصيدك الجديد: <b>{db.get_user(user_id)['points']:,}</b>")
        _forward_stars_post(msg.chat.id)
        orders_ch = db.get_config("orders_channel")
        if orders_ch:
            try:
                bot.send_message(orders_ch,
                    f" <b>شحن نجوم جديد</b>\n"
                    f" <code>{user_id}</code> شحن <b>{pts}</b> نقطة ")
            except Exception: pass

    elif payload.startswith("sub_stars_"):
        parts = payload.split("_")
        user_id = int(parts[2]); plan_id = int(parts[3])
        plan = db.get_subscription_plan(plan_id)
        if plan:
            from datetime import timedelta
            end_date = (datetime.now() + timedelta(days=plan["duration_days"])).strftime("%Y-%m-%d")
            db.create_subscription(user_id, plan_id, "stars", end_date)
            send(msg.chat.id,
                f" <b>تم تفعيل اشتراكك بنجاح!</b>\n\n"
                f"{plan['emoji']} <b>{plan['name']}</b>\n"
                f" ينتهي: <b>{end_date}</b>\n\n"
                f" أهلاً بك في الاشتراك المميز!")
            _forward_stars_post(msg.chat.id)
            orders_ch = db.get_config("orders_channel")
            if orders_ch:
                try:
                    bot.send_message(orders_ch,
                        f" <b>اشتراك جديد بالنجوم</b>\n"
                        f" <code>{user_id}</code>\n"
                        f"{plan['emoji']} {plan['name']}  {plan['duration_days']} يوم")
                except Exception: pass
        else:
            send(msg.chat.id, " حدث خطأ في تفعيل الاشتراك، تواصل مع الدعم.")

#  شحن بالكاش 
@bot.callback_query_handler(func=lambda c: c.data == "charge_cash")
def cb_charge_cash(call: CallbackQuery):
    cash_rate = db.get_config("cash_rate", "1")
    support = db.get_config("support_username", "@support")
    set_state(call.from_user.id, "charge_cash_proof")
    edit(call,
        f" <b>شحن بالكاش</b>\n\n"
        f"\n"
        f"سعر الشحن: <b>1$ = {cash_rate} نقطة</b>\n"
        f"طريقة الدفع: تواصل مع {support}\n"
        f"\n\n"
        f" بعد الدفع أرسل لقطة إثبات الدفع (صورة أو نص):",
        kb.back_keyboard("charge_menu"))

#  شحن بـ USDT 
@bot.callback_query_handler(func=lambda c: c.data == "charge_usdt")
def cb_charge_usdt(call: CallbackQuery):
    usdt_rate = db.get_config("usdt_rate", "1")
    support = db.get_config("support_username", "@support")
    wallet = db.get_config("usdt_wallet", "")
    wallet_line = f" عنوان المحفظة (TRC20):\n<code>{wallet}</code>" if wallet else f" تواصل مع {support} للحصول على عنوان المحفظة"
    set_state(call.from_user.id, "charge_usdt_proof")
    edit(call,
        f" <b>شحن بـ USDT</b>\n\n"
        f"\n"
        f"سعر الشحن: <b>1 USDT</b> = <b>{usdt_rate}</b> نقطة\n"
        f"{wallet_line}\n"
        f"\n\n"
        f" بعد الدفع أرسل لقطة إثبات التحويل:",
        kb.back_keyboard("charge_menu"))

#  شحن عبر الوكيل 
@bot.callback_query_handler(func=lambda c: c.data == "charge_reseller")
def cb_charge_reseller(call: CallbackQuery):
    reseller = db.get_reseller(call.from_user.id)
    if not reseller:
        set_state(call.from_user.id, "charge_reseller_code")
        edit(call,
            f" <b>شحن عبر الوكيل</b>\n\n"
            f"\n"
            f"أرسل كود الوكيل الخاص بك:",
            kb.back_keyboard("charge_menu"))
    else:
        discount = reseller["discount"]
        edit(call,
            f" <b>شحن عبر الوكيل</b>\n\n"
            f"\n"
            f" أنت وكيل معتمد!\n"
            f" خصمك: <b>{discount}%</b>\n"
            f"\n\n"
            f"أرسل الكمية (عدد النقاط) للشحن:",
            kb.back_keyboard("charge_menu"))
        set_state(call.from_user.id, "charge_reseller_amount")

# 
#   تحويل نقاط
# 
@bot.callback_query_handler(func=lambda c: c.data == "transfer_pts")
def cb_transfer_menu(call: CallbackQuery):
    fee_pct = db.get_config("transfer_fee_pct", "0")
    user = db.get_user(call.from_user.id)
    set_state(call.from_user.id, "transfer_waiting_id")
    edit(call,
        f" <b>تحويل النقاط</b>\n\n"
        f"\n"
        f" رصيدك: <b>{user['points']:,}</b> نقطة\n"
        f" رسوم التحويل: <b>{fee_pct}%</b>\n"
        f"\n\n"
        f"أرسل <b>ID المستخدم</b> المراد التحويل إليه:",
        kb.back_keyboard())

# 
#   المتجر
# 
@bot.callback_query_handler(func=lambda c: c.data == "shop_open")
def cb_shop_open(call: CallbackQuery):
    items = db.get_shop_items()
    user  = db.get_user(call.from_user.id)
    if not items:
        edit(call,
            f" <b>المتجر</b>\n\n"
            f" رصيدك: <b>{user['points']:,}</b> نقطة\n\n"
            f"<i>لا توجد منتجات متاحة حالياً.</i>",
            kb.back_keyboard())
        return
    text = (
        f" <b>متجر {config.BOT_NAME}</b>\n\n"
        f"\n"
        f" رصيدك: <b>{user['points']:,}</b> نقطة\n"
        f"\n\n"
    )
    for it in items:
        stock_txt = f"(متاح: {it['stock']})" if it["stock"] >= 0 else ""
        text += f"{it['emoji']} <b>{it['name']}</b>  <b>{it['price']:,}</b> نقطة {stock_txt}\n"
        if it["description"]: text += f"   <i>{it['description']}</i>\n"
    text += "\nاضغط على المنتج للشراء:"
    edit(call, text, kb.shop_keyboard(items))

@bot.callback_query_handler(func=lambda c: c.data.startswith("shop_buy_"))
def cb_shop_buy(call: CallbackQuery):
    item_id = int(call.data.split("_")[-1])
    item = db.get_shop_item(item_id)
    if not item:
        bot.answer_callback_query(call.id, " المنتج غير موجود", show_alert=True)
        return
    user = db.get_user(call.from_user.id)
    if user["points"] < item["price"]:
        bot.answer_callback_query(call.id, " نقاطك غير كافية!", show_alert=True)
        return
    if not db.deduct_points(call.from_user.id, item["price"]):
        bot.answer_callback_query(call.id, " نقاطك غير كافية!", show_alert=True)
        return
    ok = True
    err = None
    pid = db.buy_shop_item(call.from_user.id, item_id, item["name"], item["price"])
    if ok:
        user = db.get_user(call.from_user.id)
        bot.answer_callback_query(call.id,
            f" تم الشراء! سيتم التواصل معك قريباً.", show_alert=True)
        # إشعار الأدمن
        for adm in config.ADMIN_IDS:
            try:
                bot.send_message(adm,
                    f" <b>شراء جديد من المتجر!</b>\n\n"
                    f" المستخدم: <code>{call.from_user.id}</code>  {call.from_user.full_name}\n"
                    f"{item['emoji']} المنتج: <b>{item['name']}</b>\n"
                    f" الثمن: <b>{item['price']:,}</b> نقطة\n"
                    f" رصيده المتبقي: <b>{user['points']:,}</b>")
            except Exception: pass
        orders_ch = db.get_config("orders_channel")
        if orders_ch:
            try:
                bot.send_message(orders_ch,
                    f" <b>طلب متجر جديد</b>\n"
                    f" <code>{call.from_user.id}</code> اشترى {item['emoji']} <b>{item['name']}</b>")
            except Exception: pass
    else:
        bot.answer_callback_query(call.id, f" {err}", show_alert=True)

# 
#   لوحة الأدمن  قسم الشحن
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_charges")
def cb_adm_charges(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    requests_list = db.get_pending_charges()
    if not requests_list:
        edit(call, " <b>طلبات الشحن</b>\n\n<i>لا توجد طلبات معلقة.</i>",
             kb.back_keyboard("adm_back"))
        return
    text = f" <b>طلبات الشحن المعلقة ({len(requests_list)})</b>\n\n"
    for r in requests_list[:10]:
        method_names = {"stars": " نجوم", "cash": " كاش", "reseller": " وكيل"}
        mname = method_names.get(r["method"], r["method"])
        text += (f" #{r['id']} | {mname}\n"
                 f" <code>{r['user_id']}</code> |  {r['amount']:,} نقطة\n"
                 f" {r['created_at'][:16]}\n"
                 f" {r['proof'][:50] if r['proof'] else ''}\n\n")
    edit(call, text, kb.admin_charge_requests_keyboard(requests_list))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_charge_ok_"))
def cb_adm_charge_ok(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rid = int(call.data.split("_")[-1])
    r = db.get_charge_request(rid)
    if not r:
        bot.answer_callback_query(call.id, " الطلب غير موجود"); return
    db.add_points(r["user_id"], r["amount"])
    db.update_charge_status(rid, "approved", "تمت الموافقة من الأدمن")
    bot.answer_callback_query(call.id, f" تم قبول الشحن #{rid}")
    try:
        bot.send_message(r["user_id"],
            f" <b>تم قبول طلب الشحن!</b>\n\n"
            f" تم إضافة <b>{r['amount']:,}</b> نقطة لحسابك! ")
    except Exception: pass
    cb_adm_charges(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_charge_rej_"))
def cb_adm_charge_rej(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rid = int(call.data.split("_")[-1])
    r = db.get_charge_request(rid)
    if not r:
        bot.answer_callback_query(call.id, " الطلب غير موجود"); return
    db.update_charge_status(rid, "rejected", "تم الرفض من الأدمن")
    bot.answer_callback_query(call.id, f" تم رفض الطلب #{rid}")
    try:
        bot.send_message(r["user_id"],
            f" <b>تم رفض طلب الشحن #{rid}</b>\n\n"
            f"تواصل مع الدعم لمعرفة السبب.")
    except Exception: pass
    cb_adm_charges(call)

#  قناة التمويلات 
@bot.callback_query_handler(func=lambda c: c.data == "adm_orders_ch")
def cb_adm_orders_ch(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cur = db.get_config("orders_channel", "")
    set_state(call.from_user.id, "adm_set_orders_ch")
    edit(call, f" قناة التمويلات الحالية: <code>{cur}</code>\n\nأرسل ID القناة أو الرابط:",
         kb.back_keyboard("adm_back"))

#  المتجر (أدمن) 
@bot.callback_query_handler(func=lambda c: c.data == "adm_shop")
def cb_adm_shop(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    items = db.get_shop_items(only_active=False)
    edit(call,
        f" <b>إدارة المتجر</b>\n\n"
        f"عدد المنتجات: <b>{len(items)}</b>\n\n"
        f"<i>اضغط على منتج لحذفه</i>",
        kb.admin_shop_keyboard(items))

@bot.callback_query_handler(func=lambda c: c.data == "adm_shop_add")
def cb_adm_shop_add(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_shop_add")
    edit(call,
        " <b>إضافة منتج جديد</b>\n\n"
        "أرسل بهذا الشكل:\n"
        "<code>اسم المنتج||وصف المنتج|السعر بالنقاط|المخزون</code>\n\n"
        "المخزون: -1 = غير محدود\n\n"
        "<b>مثال:</b>\n"
        "<code>بوست في قناة||بوست ترويجي في قناة 10K|500|10</code>",
        kb.back_keyboard("adm_shop"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_shop_del_"))
def cb_adm_shop_del(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    item_id = int(call.data.split("_")[-1])
    db.delete_shop_item(item_id)
    bot.answer_callback_query(call.id, " تم حذف المنتج")
    cb_adm_shop(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_shop_orders")
def cb_adm_shop_orders(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    purchases = db.get_pending_purchases()
    if not purchases:
        edit(call, " <b>طلبات المتجر</b>\n\n<i>لا توجد طلبات معلقة.</i>",
             kb.back_keyboard("adm_shop"))
        return
    text = f" <b>طلبات المتجر المعلقة ({len(purchases)})</b>\n\n"
    m = InlineKeyboardMarkup()
    for p in purchases[:10]:
        text += (f" #{p['id']} | {p.get('emoji', '')} {p['item_name']}\n"
                 f" <code>{p['user_id']}</code> |  {p['points_used']:,} نقطة\n\n")
        m.row(
            kb._btn(f" تم #{p['id']}", f"adm_shop_done_{p['id']}", style="success"),
        )
    m.row(kb._btn("رجوع", "adm_shop", style="danger"))
    edit(call, text, m)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_shop_done_"))
def cb_adm_shop_done(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    pid = int(call.data.split("_")[-1])
    db.complete_purchase(pid)
    bot.answer_callback_query(call.id, " تم تأكيد الطلب")
    cb_adm_shop_orders(call)

#  الوكلاء (أدمن) 
@bot.callback_query_handler(func=lambda c: c.data == "adm_resellers")
def cb_adm_resellers(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    resellers = db.get_all_resellers()
    edit(call,
        f" <b>الوكلاء</b>\n\nعدد الوكلاء: <b>{len(resellers)}</b>",
        kb.admin_resellers_keyboard(resellers))

@bot.callback_query_handler(func=lambda c: c.data == "adm_res_add")
def cb_adm_res_add(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_add_reseller")
    edit(call,
        " <b>إضافة وكيل جديد</b>\n\n"
        "أرسل بهذا الشكل:\n"
        "<code>ID_المستخدم|كود_الوكيل|نسبة_الخصم</code>\n\n"
        "<b>مثال:</b>\n"
        "<code>123456789|AGENT1|10</code>",
        kb.back_keyboard("adm_resellers"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_res_del_"))
def cb_adm_res_del(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    user_id = int(call.data.split("_")[-1])
    db.remove_reseller(user_id)
    bot.answer_callback_query(call.id, " تم إزالة الوكيل")
    cb_adm_resellers(call)

@bot.callback_query_handler(func=lambda c: c.data == "enter_invite_code")
def cb_enter_invite_code(call: CallbackQuery):
    set_state(call.from_user.id, "waiting_invite_code")
    edit(call,
        " <b>إدخال كود هدية</b>\n\nأرسل الكود الآن:",
        kb.back_keyboard())

# 
#   قنوات النقاط
# 
@bot.callback_query_handler(func=lambda c: c.data == "points_channels")
def cb_points_channels(call: CallbackQuery):
    channels = db.get_points_channels()
    if not channels:
        edit(call, " <b>قنوات النقاط</b>\n\n<i>لا توجد قنوات حالياً.</i>",
             kb.back_keyboard("collect_section"))
        return
    text = " <b>اشترك في القنوات واجمع النقاط!</b>\n\n\n"
    for ch in channels:
        text += f" {ch['channel_name']}  <b>+{ch['points_reward']}</b> \n"
    text += "\n\n<i>اشترك ثم اضغط  جمّعت نقاطي</i>"
    edit(call, text, kb.points_channels_keyboard(channels))

@bot.callback_query_handler(func=lambda c: c.data == "collect_points")
def cb_collect_points(call: CallbackQuery):
    tg_id = call.from_user.id
    earned = 0
    for ch in db.get_points_channels():
        if db.has_earned_channel_points(tg_id, ch["channel_id"]): continue
        try:
            member = bot.get_chat_member(ch["channel_id"], tg_id)
            if member.status not in ("left", "kicked"):
                db.add_points(tg_id, ch["points_reward"])
                db.mark_channel_points_earned(tg_id, ch["channel_id"])
                earned += ch["points_reward"]
        except Exception: pass
    if earned > 0:
        bot.answer_callback_query(call.id, f" حصلت على {earned} نقطة!", show_alert=True)
    else:
        bot.answer_callback_query(call.id, " لم تحصل على نقاط جديدة.", show_alert=True)
    cb_collect_section(call)

#  التحقق من الاشتراك الإجباري 
@bot.callback_query_handler(func=lambda c: c.data.startswith("check_sub_"))
def cb_check_sub(call: CallbackQuery):
    ok, missing = sync_check_subscriptions(call.from_user.id)
    if ok:
        # منح نقاط الإحالة المعلقة بعد التحقق من الاشتراك
        referrer_id, ref_pts = db.award_pending_referral(call.from_user.id)
        if referrer_id and ref_pts:
            # ── إشعار المُحيل (صاحب الرابط) ──
            try:
                ref_user = db.get_user(referrer_id)
                bot.send_message(
                    referrer_id,
                    f"🎉 <b>إحالة ناجحة!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 <b>{call.from_user.first_name}</b> اشترك في القنوات عبر رابطك\n"
                    f"⭐️ ربحت <b>+{ref_pts}</b> نقطة\n"
                    f"💰 رصيدك الآن: <b>{ref_user['points'] if ref_user else '?':,}</b> نقطة\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"<i>استمر في مشاركة رابطك لمزيد من النقاط!</i>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
            # ── إشعار المُحال (الشخص الذي استخدم الرابط) ──
            try:
                referrer_user = db.get_user(referrer_id)
                referrer_name = referrer_user["full_name"] if referrer_user else "صديقك"
                my_user = db.get_user(call.from_user.id)
                bot.send_message(
                    call.from_user.id,
                    f"✅ <b>إحالتك تمت بنجاح!</b>\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"👤 لقد انضممت عبر رابط <b>{referrer_name}</b>\n"
                    f"⭐️ تمت إضافة <b>{ref_pts}</b> نقطة لحسابه\n"
                    f"💰 رصيدك الحالي: <b>{my_user['points'] if my_user else '?':,}</b> نقطة\n"
                    f"━━━━━━━━━━━━━━━\n"
                    f"<i>شارك رابطك أنت أيضاً واكسب نقاطاً!</i>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        bot.answer_callback_query(call.id, "تم التحقق! أهلاً بك.", show_alert=True)
        cb_back_main(call)
    else:
        bot.answer_callback_query(call.id, f"لم تشترك بعد في {len(missing)} قناة!", show_alert=True)

# 
#   خدماتي (الأقسام)
# 
@bot.callback_query_handler(func=lambda c: c.data == "my_services")
def cb_my_services(call: CallbackQuery):
    ok, missing = sync_check_subscriptions(call.from_user.id)
    if not ok:
        edit(call, " <b>اشترك في القنوات أولاً:</b>", kb.subscribe_keyboard(missing, call.from_user.id))
        return
    apps = db.get_apps()
    if not apps:
        edit(call,
            " <b>خدماتي</b>\n\n<i>لا توجد أقسام متاحة حالياً.\nالأدمن لم يضف أي تطبيقات بعد.</i>",
            kb.back_keyboard())
        return
    text = (
        f" <b>خدماتي  اختر التطبيق</b>\n\n"
        f"\n"
        f"اختر القسم الذي تريد شراء خدمات منه:\n"
        f""
    )
    edit(call, text, kb.services_apps_keyboard(apps))

@bot.callback_query_handler(func=lambda c: c.data.startswith("app_"))
def cb_open_app(call: CallbackQuery):
    app_id = int(call.data.split("_")[1])
    app = db.get_app(app_id)
    if not app:
        bot.answer_callback_query(call.id, " القسم غير موجود")
        return
    services = db.get_app_services(app_id)
    user = db.get_user(call.from_user.id)
    if not services:
        edit(call,
            f"{app['emoji']} <b>{app['name']}</b>\n\n<i>لا توجد خدمات في هذا القسم.</i>",
            kb.back_keyboard("my_services"))
        return
    text = (
        f"{app['emoji']} <b>{app['name']}</b>\n\n"
        f"\n"
        f" رصيدك: <b>{user['points']:,}</b> نقطة\n"
        f"\n\n"
        f"اختر الخدمة المطلوبة:"
    )
    edit(call, text, kb.app_services_keyboard(app_id, services))

@bot.callback_query_handler(func=lambda c: c.data.startswith("svc_"))
def cb_open_service(call: CallbackQuery):
    svc_id = int(call.data.split("_")[1])
    svc = db.get_service(svc_id)
    if not svc:
        bot.answer_callback_query(call.id, " الخدمة غير موجودة")
        return
    app = db.get_app(svc["app_id"])
    user = db.get_user(call.from_user.id)
    max_can = user["points"] // svc["points_per_unit"] if svc["points_per_unit"] > 0 else 0

    set_state(call.from_user.id, "svc_waiting_link",
              svc_id=svc_id, app_id=svc["app_id"])

    edit(call,
        f"{svc['emoji']} <b>{svc['name']}</b>\n"
        f" القسم: {app['emoji']} {app['name']}\n\n"
        f"\n"
        f" السعر: <b>{svc['points_per_unit']}</b> نقطة/وحدة\n"
        
        f" الحد الأقصى: <b>{svc['max_qty']:,}</b>\n"
        f" نقاطك: <b>{user['points']:,}</b>\n"
        f" يمكنك طلب: <b>{max_can:,}</b> وحدة\n"
        f"\n\n"
        f" <b>الخطوة 1/2:</b> أرسل الرابط المطلوب ",
        kb.back_keyboard(f"app_{svc['app_id']}"))

@bot.message_handler(func=lambda m: get_state(m.from_user.id).get("state") == "svc_waiting_link")
def msg_svc_link(msg: Message):
    link = msg.text.strip()
    if not (link.startswith("http") or "t.me" in link or "tiktok" in link or
            "instagram" in link or "youtube" in link or "youtu.be" in link or link.startswith("@")):
        send(msg.chat.id, " الرابط غير صحيح! أرسل رابطاً صحيحاً.")
        return
    d = get_state(msg.from_user.id)["data"]
    svc = db.get_service(d["svc_id"])
    if not svc:
        send(msg.chat.id, " الخدمة لم تعد متاحة.", kb.back_keyboard("my_services"))
        clear_state(msg.from_user.id); return

    set_state(msg.from_user.id, "svc_waiting_qty", svc_id=d["svc_id"], app_id=d["app_id"], link=link)
    send(msg.chat.id,
        f" <b>تم استلام الرابط</b>\n<code>{link}</code>\n\n"
        f"\n"
        f" <b>الخطوة 2/2:</b> أرسل الكمية المطلوبة\n"
        
        f"",
        kb.back_keyboard(f"app_{d['app_id']}"))

@bot.message_handler(func=lambda m: get_state(m.from_user.id).get("state") == "svc_waiting_qty")
def msg_svc_qty(msg: Message):
    try: qty = int(msg.text.strip().replace(",", ""))
    except ValueError:
        send(msg.chat.id, " الكمية يجب أن تكون رقماً!"); return
    d = get_state(msg.from_user.id)["data"]
    svc = db.get_service(d["svc_id"])
    if not svc:
        send(msg.chat.id, " الخدمة غير متاحة.", kb.back_keyboard("my_services"))
        clear_state(msg.from_user.id); return
    if qty < svc["min_10"] or qty > svc["max_qty"]:
        send(msg.chat.id,
            f" الكمية يجب أن تكون بين {svc['min_10']:,} و {svc['max_qty']:,}!")
        return

    pts_needed = qty * svc["points_per_unit"]
    user = db.get_user(msg.from_user.id)
    set_state(msg.from_user.id, "svc_confirm",
              svc_id=d["svc_id"], app_id=d["app_id"], link=d["link"],
              qty=qty, pts_needed=pts_needed)

    enough = user["points"] >= pts_needed
    warn = "" if enough else f"\n\n <b>نقاطك غير كافية!</b> ينقصك <b>{pts_needed - user['points']:,}</b> نقطة."
    app = db.get_app(svc["app_id"])

    send(msg.chat.id,
        f" <b>تأكيد الطلب</b>\n\n"
        f"\n"
        f" القسم: {app['emoji']} {app['name']}\n"
        f" الخدمة: {svc['emoji']} {svc['name']}\n"
        f" الرابط: <code>{d['link']}</code>\n"
        f" الكمية: <b>{qty:,}</b>\n"
        f" التكلفة: <b>{pts_needed:,}</b> نقطة\n"
        f" رصيدك: <b>{user['points']:,}</b>\n"
        f"{warn}",
        kb.confirm_order_keyboard() if enough else kb.back_keyboard("my_services"))

@bot.callback_query_handler(func=lambda c: c.data == "order_confirm")
def cb_order_confirm(call: CallbackQuery):
    state = get_state(call.from_user.id)
    s = state.get("state")
    d = state.get("data", {})
    if s == "svc_confirm":
        return _confirm_service_order(call, d)
    elif s == "confirm_order":  # تمويل قنوات (التدفق القديم)
        return _confirm_fund_order(call, d)
    else:
        bot.answer_callback_query(call.id, " انتهت الجلسة، ابدأ من جديد.")

def _confirm_service_order(call, d):
    svc = db.get_service(d["svc_id"])
    if not svc:
        bot.answer_callback_query(call.id, " الخدمة لم تعد متاحة")
        return
    pts_needed = d["pts_needed"]
    qty = d["qty"]
    link = d["link"]

    if not db.deduct_points(call.from_user.id, pts_needed):
        bot.answer_callback_query(call.id, " نقاطك غير كافية!", show_alert=True)
        return

    charge = round((qty / 1000) * float(svc["price_per_1000"] or 0.5), 4)
    result = smm.create_order(svc["api_service_id"], link, qty)
    api_order = str(result.get("order", ""))
    error = result.get("error", "")
    app = db.get_app(svc["app_id"])

    order_id = db.create_order(
        call.from_user.id, svc["api_service_id"], svc["name"],
        link, qty, charge, points_used=pts_needed,
        api_order_id=api_order if api_order else None,
        app_name=f"{app['emoji']} {app['name']}" if app else "")
    #  احفظ عدد أعضاء القناة الحالي كنقطة بداية (قبل التمويل) 
    start_count = -1
    # حاول جلب العدد الحقيقي من تليجرام
    for _attempt in range(3):
        try:
            # حاول أولاً مع الرابط كما هو، ثم بعد تحويله لـ @username أو chat_id
            chat_identifier = link
            if "t.me/" in link:
                part = link.split("t.me/")[-1].split("?")[0].strip("/")
                chat_identifier = f"@{part}" if not part.startswith("+") else link
            start_count = bot.get_chat_member_count(chat_identifier)
            if start_count >= 0:
                break
        except Exception as e:
            print(f"[order #{order_id}] محاولة {_attempt+1} فشل جلب start_members: {e}")
            try:
                # محاولة بديلة: get_chat أولاً للحصول على chat_id الرقمي
                chat_obj = bot.get_chat(link)
                start_count = bot.get_chat_member_count(chat_obj.id)
                if start_count >= 0:
                    break
            except Exception as e2:
                print(f"[order #{order_id}] محاولة بديلة فشلت: {e2}")
    if start_count >= 0:
        db.set_order_start_members(order_id, start_count)
        print(f"[order #{order_id}] start_members = {start_count}")
    else:
        # لا نضع 0 لأنه سيخطئ الحساب - نترك الـ tracker يجلبها
        db.set_order_start_members(order_id, -1)
        print(f"[order #{order_id}] start_members لم يُجلب - سيحاول الـ tracker لاحقاً")
    #  ابدأ تتبع الطلب فوراً 
    _ensure_order_tracked(order_id)
    clear_state(call.from_user.id)

    if error:
        db.add_points(call.from_user.id, pts_needed)
        db.update_order_status(order_id, "canceled")
        edit(call, f" <b>فشل الطلب!</b>\n\n{error}\n\n<i>تم استرداد نقاطك.</i>", kb.back_keyboard())
        return
    user = db.get_user(call.from_user.id)
    edit(call,
        f" <b>تم إرسال الطلب بنجاح!</b>\n\n"
        f" رقم الطلب: <b>#{order_id}</b>\n"
        f" الخدمة: {svc['emoji']} {svc['name']}\n"
        f" الكمية: {qty:,}\n"
        f" النقاط المستخدمة: {pts_needed:,}\n"
        f" رصيدك المتبقي: {user['points']:,}\n"
        f"\n\n"
        f"<i>سيصلك إشعار فور اكتمال الطلب </i>",
        kb.back_keyboard())
    # إشعار قناة التمويلات
    orders_ch = db.get_config("orders_channel")
    if orders_ch:
        try:
            bot.send_message(orders_ch,
                f" <b>طلب جديد #{order_id}</b>\n"
                f" <code>{call.from_user.id}</code>  {call.from_user.full_name}\n"
                f" {svc['emoji']} {svc['name']}\n"
                f" {qty:,} وحدة |  {pts_needed:,} نقطة")
        except Exception: pass

# 
#   تمويل قنوات (التدفق القديم)
# 
@bot.callback_query_handler(func=lambda c: c.data == "fund_start")
def cb_fund_start(call: CallbackQuery):
    ok, missing = sync_check_subscriptions(call.from_user.id)
    if not ok:
        edit(call, " <b>اشترك في القنوات أولاً:</b>",
             kb.subscribe_keyboard(missing, call.from_user.id))
        return
    service_id = db.get_config("service_id")
    if not service_id:
        edit(call, " <b>الخدمة غير متاحة حالياً.</b>", kb.back_keyboard())
        return
    pts_per_member = int(db.get_config("points_per_member", "1"))
    svc_min = db.get_config("service_min", "10")
    svc_max = db.get_config("service_max", "100000")
    user    = db.get_user(call.from_user.id)
    max_can = user["points"] // pts_per_member if pts_per_member > 0 else 0
    edit(call,
        f" <b>تمويل  اختر النوع</b>\n\n"
        f"\n"
        f" السعر: <b>{pts_per_member}</b> نقطة/عضو\n"
        f" من {svc_min} إلى {svc_max} عضو\n"
        f" نقاطك: <b>{user['points']:,}</b>\n"
        f" تقدر تمول: <b>{max_can:,}</b> عضو\n"
        f"\n\n"
        f" <b>اختر نوع المنصة:</b>",
        kb.fund_type_keyboard())

@bot.message_handler(func=lambda m: get_state(m.from_user.id).get("state") == "waiting_quantity")
def msg_fund_qty(msg: Message):
    try: qty = int(msg.text.strip().replace(",", ""))
    except ValueError:
        send(msg.chat.id, " الكمية يجب أن تكون رقماً!"); return
    d = get_state(msg.from_user.id)["data"]
    svc_min = int(d.get("svc_min", 10)); svc_max = int(d.get("svc_max", 100000))
    if qty < svc_min or qty > svc_max:
        send(msg.chat.id, f" الكمية بين {svc_min:,} و {svc_max:,}!"); return
    fund_type = d.get("fund_type", "channel")
    set_state(msg.from_user.id, "waiting_link", **d, qty=qty)
    ch_or_gr = "القناة" if fund_type == "channel" else "الجروب"
    send(msg.chat.id,
        f" تم تسجيل العدد: <b>{qty:,}</b> عضو\n\n"
        f" <b>الخطوة 2/2  أرسل معرف {ch_or_gr}</b>\n\n"
        f"\n"
        f" 1⃣ أضف البوت إلى {ch_or_gr}\n"
        f" 2⃣ رقّه إلى مشرف وأعطه صلاحية <b>دعوة المستخدمين</b>\n"
        f" 3⃣ أرسل معرف {ch_or_gr} أو رابطها العام\n"
        f"\n\n"
        f"<i>~ اقرأ الخطوات جيداً </i>",
        kb.back_keyboard())

@bot.message_handler(func=lambda m: get_state(m.from_user.id).get("state") == "waiting_link",
                     content_types=['text', 'photo', 'video', 'document', 'sticker', 'audio', 'voice'])
def msg_fund_link(msg: Message):
    #  استخراج معرف القناة 
    # 1) توجيه (forward) من قناة
    if msg.forward_from_chat:
        chat_obj = msg.forward_from_chat
        link = f"@{chat_obj.username}" if chat_obj.username else str(chat_obj.id)
    elif msg.text:
        raw = msg.text.strip()
        # تنظيف الرابط: https://t.me/username → @username
        if "t.me/" in raw:
            part = raw.split("t.me/")[-1].split("?")[0].strip("/")
            link = f"@{part}" if not part.startswith("+") else raw
        elif raw.startswith("@"):
            link = raw
        elif raw.startswith("-"):
            # chat_id سالب (قناة خاصة)
            link = raw
        else:
            # يوزر بدون @  أضفه
            clean = raw.lstrip("@").strip()
            if clean and (clean.replace("_", "").isalnum()):
                link = f"@{clean}"
            else:
                send(msg.chat.id,
                    " <b>الصيغة غير صحيحة!</b>\n\n"
                    "أرسل واحداً من:\n"
                    " <code>@username</code>\n"
                    " <code>https://t.me/username</code>\n"
                    " حوّل أي رسالة من القناة مباشرة",
                    kb.back_keyboard())
                return
    else:
        send(msg.chat.id,
            " أرسل يوزر القناة أو رابطها أو حوّل رسالة منها!",
            kb.back_keyboard())
        return

    #  تحقق إن البوت موجود ومشرف في القناة 
    try:
        chat_info = bot.get_chat(link)
        chat_id   = chat_info.id          # نستخدم الـ id الرقمي دايماً من هنا
        member    = bot.get_chat_member(chat_id, bot.get_me().id)
        if member.status not in ("administrator", "creator"):
            send(msg.chat.id,
                " <b>البوت ليس مشرفاً في القناة!</b>\n\n"
                "\n"
                " 1⃣ أضف البوت للقناة\n"
                " 2⃣ اجعله مشرف وأعطه صلاحية <b>دعوة المستخدمين</b>\n"
                " 3⃣ أعد إرسال الرابط\n"
                "",
                kb.back_keyboard())
            return
        # استخدم الـ username لو موجود وإلا الـ id
        link = f"@{chat_info.username}" if chat_info.username else str(chat_id)
    except Exception as e:
        err = str(e)
        print(f"[msg_fund_link] get_chat error: link={link} | {err}")
        send(msg.chat.id,
            f" <b>تعذّر الوصول للقناة!</b>\n\n"
            f"تأكد من:\n"
            f" أن البوت <b>أدمن</b> في القناة\n"
            f" أن اليوزر أو الرابط صحيح\n\n"
            f"<i>أو حوّل رسالة من القناة مباشرة</i>",
            kb.back_keyboard())
        return
    d = get_state(msg.from_user.id)["data"]
    qty = d.get("qty", 0)
    pts_per_member = int(d.get("pts_per_member", 1))
    points_needed = qty * pts_per_member
    user = db.get_user(msg.from_user.id)
    if user["points"] < points_needed:
        send(msg.chat.id,
            f" <b>نقاطك غير كافية!</b>\n\n"
            f" التكلفة: <b>{points_needed:,}</b> نقطة\n"
            f" رصيدك: <b>{user['points']:,}</b>\n"
            f" ينقصك <b>{points_needed - user['points']:,}</b> نقطة!",
            kb.back_keyboard()); clear_state(msg.from_user.id); return

    svc_id = d.get("service_id"); svc_nm = d.get("service_name", "تمويل")

    if not db.deduct_points(msg.from_user.id, points_needed):
        send(msg.chat.id, " نقاطك غير كافية!", kb.back_keyboard()); clear_state(msg.from_user.id); return
    price_per_k = float(db.get_config("price_per_1000", "0.5"))
    charge = round((qty / 1000) * price_per_k, 4)
    result = smm.create_order(svc_id, link, qty)
    api_order = str(result.get("order", ""))
    error = result.get("error", "")

    order_id = db.create_order(msg.from_user.id, svc_id, svc_nm, link, qty, charge,
                               points_used=points_needed,
                               api_order_id=api_order if api_order else None,
                               app_name=" تمويل قنوات")
    #  احفظ عدد أعضاء القناة الحالي كنقطة بداية (قبل التمويل) 
    start_count = -1
    try:
        start_count = bot.get_chat_member_count(chat_id)
        if start_count >= 0:
            db.set_order_start_members(order_id, start_count)
            print(f"[order #{order_id}] start_members = {start_count}")
    except Exception as e:
        print(f"[order #{order_id}] فشل جلب start_members (chat_id): {e}")
        try:
            start_count = bot.get_chat_member_count(link)
            if start_count >= 0:
                db.set_order_start_members(order_id, start_count)
                print(f"[order #{order_id}] start_members (link) = {start_count}")
        except Exception as e2:
            print(f"[order #{order_id}] فشل جلب start_members (link): {e2}")
    if start_count < 0:
        db.set_order_start_members(order_id, -1)
        print(f"[order #{order_id}] start_members لم يُجلب - سيحاول الـ tracker لاحقاً")
    #  ابدأ تتبع الطلب فوراً 
    _ensure_order_tracked(order_id)
    clear_state(msg.from_user.id)
    if error:
        db.add_points(msg.from_user.id, points_needed)
        db.update_order_status(order_id, "canceled")
        send(msg.chat.id, f" <b>فشل الطلب!</b>\n\n{error}\n\n<i>تم استرداد نقاطك.</i>", kb.back_keyboard()); return
    send(msg.chat.id,
        f"• تم خصم ({points_needed:,}) نقاط\n"
        f"- وبدء تمويل قناتك {qty:,} عضو 🚸\n\n"
        f"- اذا قمت بطرد البوت من القناة او تنزيله من الادمنيه اثناء التمويل سيتم استبعاد قناتك !!!",
        kb.back_keyboard())
    #  إشعار قناة الطلبات 
    orders_ch = db.get_config("orders_channel")
    if orders_ch:
        try:
            bot.send_message(orders_ch,
                f"<b>طلب تمويل جديد #{order_id}</b>\n"
                f"- المستخدم: {msg.from_user.full_name}\n"
                f" {link}\n"
                f" {qty:,} عضو |  {points_needed:,} نقطة",
                parse_mode="HTML")
        except Exception: pass

def _confirm_fund_order(call, d):
    points_needed = d["points_needed"]; qty = d["qty"]
    link = d["link"]; svc_id = d["service_id"]; svc_nm = d.get("service_name", "تمويل")

    if not db.deduct_points(call.from_user.id, points_needed):
        bot.answer_callback_query(call.id, " نقاطك غير كافية!", show_alert=True); return
    price_per_k = float(db.get_config("price_per_1000", "0.5"))
    charge = round((qty / 1000) * price_per_k, 4)
    result = smm.create_order(svc_id, link, qty)
    api_order = str(result.get("order", ""))
    error = result.get("error", "")

    order_id = db.create_order(call.from_user.id, svc_id, svc_nm, link, qty, charge,
                               points_used=points_needed,
                               api_order_id=api_order if api_order else None,
                               app_name=" تمويل قنوات")
    #  احفظ عدد أعضاء القناة الحالي كنقطة بداية (قبل التمويل) 
    start_count = -1
    for _attempt in range(3):
        try:
            chat_identifier = link
            if "t.me/" in link:
                part = link.split("t.me/")[-1].split("?")[0].strip("/")
                chat_identifier = f"@{part}" if not part.startswith("+") else link
            start_count = bot.get_chat_member_count(chat_identifier)
            if start_count >= 0:
                break
        except Exception as e:
            print(f"[order #{order_id}] محاولة {_attempt+1} فشل start_members: {e}")
            try:
                chat_obj = bot.get_chat(link)
                start_count = bot.get_chat_member_count(chat_obj.id)
                if start_count >= 0:
                    break
            except Exception as e2:
                print(f"[order #{order_id}] محاولة بديلة فشلت: {e2}")
    if start_count >= 0:
        db.set_order_start_members(order_id, start_count)
        print(f"[order #{order_id}] start_members = {start_count}")
    else:
        db.set_order_start_members(order_id, -1)
        print(f"[order #{order_id}] start_members لم يُجلب - سيحاول الـ tracker لاحقاً")
    #  ابدأ تتبع الطلب فوراً 
    _ensure_order_tracked(order_id)
    clear_state(call.from_user.id)

    if error:
        db.add_points(call.from_user.id, points_needed)
        db.update_order_status(order_id, "canceled")
        edit(call, f" <b>فشل الطلب!</b>\n\n{error}\n\n<i>تم استرداد نقاطك.</i>", kb.back_keyboard())
        return

    user = db.get_user(call.from_user.id)
    edit(call,
        f"• تم خصم ({points_needed:,}) نقاط\n"
        f"- وبدء تمويل قناتك {qty:,} عضو 🚸\n\n"
        f"- اذا قمت بطرد البوت من القناة او تنزيله من الادمنيه اثناء التمويل سيتم استبعاد قناتك !!!",
        kb.back_keyboard())
    #  إشعار قناة الطلبات 
    orders_ch = db.get_config("orders_channel")
    if orders_ch:
        try:
            bot.send_message(orders_ch,
                f"<b>طلب تمويل جديد #{order_id}</b>\n"
                f"- المستخدم: {call.from_user.full_name}\n"
                f" {link}\n"
                f" {qty:,} عضو |  {points_needed:,} نقطة",
                parse_mode="HTML")
        except Exception: pass

# 
#   لوحة الأدمن
# 
@bot.message_handler(commands=["admin"])
def cmd_admin(msg: Message):
    if not is_admin(msg.from_user.id):
        send(msg.chat.id, " ليس لديك صلاحية."); return
    smm_bal = smm.get_balance()
    total_u = db.get_users_count()
    total_o, today_o, revenue, today_rev, total_pts = db.get_orders_stats()
    send(msg.chat.id,
        f" <b>لوحة الأدمن  {config.BOT_NAME}</b>\n\n"
        f"\n"
        f" المستخدمون: <b>{total_u}</b>\n"
        f" الطلبات: <b>{total_o}</b> (اليوم: {today_o})\n"
        f" نقاط مستخدمة: <b>{total_pts:,}</b>\n"
        f" الأرباح: <b>{revenue:.2f}$</b>\n"
        f" SMMParty: <b>{smm_bal:.2f}$</b>\n"
        f"",
        kb.admin_main_keyboard())

@bot.message_handler(commands=["db"])
def cmd_db(msg: Message):
    if not is_admin(msg.from_user.id):
        send(msg.chat.id, " ليس لديك صلاحية."); return
    tables = _db_table_info()
    total = sum(tables.values())
    text = (
        f" <b>إدارة قاعدة البيانات</b>\n\n"
        f"عدد الجداول: <b>{len(tables)}</b>\n"
        f"إجمالي السجلات: <b>{total:,}</b>\n\n"
        f"اختر ما تريد:"
    )
    send(msg.chat.id, text, kb_db_main())

@bot.callback_query_handler(func=lambda c: c.data == "adm_back")
def cb_adm_back(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    clear_state(call.from_user.id)
    cmd_admin_inline(call)

def cmd_admin_inline(call):
    smm_bal = smm.get_balance()
    total_u = db.get_users_count()
    total_o, today_o, revenue, today_rev, total_pts = db.get_orders_stats()
    edit(call,
        f" <b>لوحة الأدمن</b>\n\n"
        f" {total_u} |  {total_o} (اليوم {today_o})\n"
        f" {total_pts:,} نقطة |  {revenue:.2f}$\n"
        f" SMMParty: {smm_bal:.2f}$",
        kb.admin_main_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "adm_close")
def cb_adm_close(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try: bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception: pass

#  إدارة الأقسام والخدمات (طريقة سهلة جداً) 
@bot.callback_query_handler(func=lambda c: c.data == "adm_apps")
def cb_adm_apps(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    apps = db.get_apps(only_active=False)
    edit(call,
        f" <b>إدارة الأقسام والخدمات</b>\n\n"
        f"\n"
        f"عدد الأقسام: <b>{len(apps)}</b>\n"
        f"\n\n"
        f"<i>اختر قسماً لعرض/إضافة خدماته</i>",
        kb.admin_apps_keyboard(apps))

@bot.callback_query_handler(func=lambda c: c.data == "adm_add_app")
def cb_adm_add_app(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_add_app")
    edit(call,
        " <b>إضافة قسم جديد</b>\n\n"
        "أرسل اسم القسم والإيموجي بهذا الشكل:\n"
        "<code>تيك توك|</code>\n\n"
        "<i>مثال آخر:</i>\n"
        "<code>انستجرام|</code>\n"
        "<code>يوتيوب|</code>",
        kb.back_keyboard("adm_apps"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_app_"))
def cb_adm_view_app(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    app_id = int(call.data.split("_")[-1])
    app = db.get_app(app_id)
    if not app:
        bot.answer_callback_query(call.id, " القسم غير موجود"); return
    services = db.get_app_services(app_id, only_active=False)
    edit(call,
        f"{app['emoji']} <b>{app['name']}</b>\n\n"
        f"\n"
        f"عدد الخدمات: <b>{len(services)}</b>\n"
        f"",
        kb.admin_app_view_keyboard(app_id, services))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_app_"))
def cb_adm_del_app(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    app_id = int(call.data.split("_")[-1])
    db.delete_app(app_id)
    bot.answer_callback_query(call.id, " تم حذف القسم")
    cb_adm_apps(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_add_svc_"))
def cb_adm_add_svc(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    app_id = int(call.data.split("_")[-1])
    set_state(call.from_user.id, "adm_add_svc", app_id=app_id)
    edit(call,
        " <b>إضافة خدمة جديدة (مبسّطة)</b>\n\n"
        " الآن إضافة الخدمة أسهل من أي وقت!\n"
        "فقط أرسل: <b>Service ID</b> + <b>السعر بالنقاط</b>\n"
        "والبوت يجيب باقي البيانات تلقائياً من الموقع \n\n"
        "<b>الشكل:</b>\n"
        "<code>SERVICE_ID|نقاط_الوحدة</code>\n\n"
        "<b>أو لو عاوز تخصيص أكتر:</b>\n"
        "<code>SERVICE_ID|نقاط_الوحدة|الإيموجي|اسم_مخصص</code>\n\n"
        "<b>أمثلة:</b>\n"
        " <code>1234|2</code>\n"
        " <code>5678|1||متابعين تيك توك VIP</code>\n\n"
        "<i> الاسم والحد الأدنى/الأقصى يُجلبون تلقائياً من SMMParty</i>",
        kb.back_keyboard(f"adm_app_{app_id}"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_svc_"))
def cb_adm_view_svc(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    svc_id = int(call.data.split("_")[-1])
    svc = db.get_service(svc_id)
    if not svc:
        bot.answer_callback_query(call.id, " غير موجودة"); return
    edit(call,
        f"{svc['emoji']} <b>{svc['name']}</b>\n\n"
        f"\n"
        f" API ID: <code>{svc['api_service_id']}</code>\n"
        f" السعر: <b>{svc['points_per_unit']}</b> نقطة/وحدة\n"
        f" الحدود: {svc['min_10']:,} - {svc['max_qty']:,}\n"
        f" سعر/1000: <b>{svc['price_per_1000']}$</b>\n"
        f"",
        kb.admin_service_view_keyboard(svc_id, svc["app_id"]))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_svc_"))
def cb_adm_del_svc(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    svc_id = int(call.data.split("_")[-1])
    svc = db.get_service(svc_id)
    app_id = svc["app_id"] if svc else None
    db.delete_service(svc_id)
    bot.answer_callback_query(call.id, " تم الحذف")
    if app_id:
        call.data = f"adm_app_{app_id}"
        cb_adm_view_app(call)
    else:
        cb_adm_apps(call)

#  إعدادات الخدمة الافتراضية (تمويل القنوات) 
@bot.callback_query_handler(func=lambda c: c.data == "adm_service")
def cb_adm_service(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    edit(call, " <b>إعدادات تمويل القنوات (الافتراضي)</b>", kb.admin_service_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "adm_view_service")
def cb_adm_view_service(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    edit(call,
        f" <b>إعدادات الخدمة:</b>\n\n"
        f" Service ID: <code>{db.get_config('service_id', '')}</code>\n"
        f" السعر/1000: <b>{db.get_config('price_per_1000', '0.5')}$</b>\n"
        f" سعر العضو: <b>{db.get_config('points_per_member', '1')}</b> نقطة\n"
        f" من {db.get_config('service_min', '10')} إلى {db.get_config('service_max', '100000')}",
        kb.admin_service_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_service_id")
def cb_adm_set_service_id(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_set_service_id")
    edit(call, " أرسل Service ID:", kb.back_keyboard("adm_service"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_price")
def cb_adm_set_price(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_set_price")
    edit(call, " أرسل السعر/10 ($):", kb.back_keyboard("adm_service"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_min_qty")
def cb_adm_set_min_qty(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    current = db.get_config("service_min", "10")
    set_state(call.from_user.id, "adm_set_min_qty")
    edit(call,
        f" <b>تغيير الحد الأدنى للتمويل</b>\n\n"
        f"الحد الحالي: <b>{current}</b> عضو\n\n"
        f"أرسل الرقم الجديد:",
        kb.back_keyboard("adm_service"))

#  إعدادات الشحن (أدمن) 
@bot.callback_query_handler(func=lambda c: c.data == "adm_charge_settings")
def cb_adm_charge_settings(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    stars      = db.get_config("stars_per_point", "1")
    cash       = db.get_config("cash_rate", "1")
    usdt       = db.get_config("usdt_rate", "1")
    wallet     = db.get_config("usdt_wallet", "غير محدد")
    stars_post = db.get_config("stars_post_link", "")
    post_line  = f"<code>{stars_post}</code>" if stars_post else "<i>غير محدد</i>"
    edit(call,
        f" <b>إعدادات الشحن</b>\n\n"
        f"\n"
        f" النجوم: <b>1 نجمة = {stars} نقطة</b>\n"
        f"⭐ منشور النجوم: {post_line}\n"
        f" الكاش: <b>1$ = {cash} نقطة</b>\n"
        f" USDT: <b>1 USDT = {usdt} نقطة</b>\n"
        f" محفظة USDT: <code>{wallet}</code>\n"
        f"",
        kb.admin_charge_settings_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "adm_view_charge_settings")
def cb_adm_view_charge_settings(call: CallbackQuery):
    cb_adm_charge_settings(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_stars_rate")
def cb_adm_set_stars_rate(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cur = db.get_config("stars_per_point", "1")
    set_state(call.from_user.id, "adm_set_stars_rate")
    edit(call,
        f" <b>سعر النجوم</b>\n\nالحالي: <b>1 نجمة = {cur} نقطة</b>\n\nأرسل عدد النقاط لكل نجمة:",
        kb.back_keyboard("adm_charge_settings"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_stars_post")
def cb_adm_set_stars_post(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cur = db.get_config("stars_post_link", "")
    cur_line = f"الحالي: <code>{cur}</code>" if cur else "الحالي: <i>غير محدد</i>"
    set_state(call.from_user.id, "adm_set_stars_post")
    edit(call,
        f"⭐ <b>منشور استقبال النجوم</b>\n\n"
        f"{cur_line}\n\n"
        f"أرسل رابط المنشور، مثال:\n"
        f"<code>https://t.me/mychannel/5</code>\n"
        f"أو رابط خاص:\n"
        f"<code>https://t.me/c/1234567890/5</code>\n\n"
        f"بعد كل شراء بالنجوم يوصل المشتري forward من هذا المنشور.\n\n"
        f"<i>أرسل 0 لإلغاء الربط</i>",
        kb.back_keyboard("adm_charge_settings"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_cash_rate")
def cb_adm_set_cash_rate(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cur = db.get_config("cash_rate", "1")
    set_state(call.from_user.id, "adm_set_cash_rate")
    edit(call,
        f" <b>سعر الكاش</b>\n\nالحالي: <b>1$ = {cur} نقطة</b>\n\nأرسل عدد النقاط لكل دولار:",
        kb.back_keyboard("adm_charge_settings"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_usdt_rate")
def cb_adm_set_usdt_rate(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cur_rate   = db.get_config("usdt_rate", "1")
    cur_wallet = db.get_config("usdt_wallet", "غير محدد")
    set_state(call.from_user.id, "adm_set_usdt_rate")
    edit(call,
        f" <b>إعدادات USDT</b>\n\n"
        f"السعر الحالي: <b>1 USDT = {cur_rate} نقطة</b>\n"
        f"المحفظة الحالية: <code>{cur_wallet}</code>\n\n"
        f"أرسل بهذا الشكل:\n<code>النقاط|عنوان_المحفظة</code>\n\n"
        f"مثال: <code>5000|TRX123abc...</code>",
        kb.back_keyboard("adm_charge_settings"))

#  إعدادات النقاط 
@bot.callback_query_handler(func=lambda c: c.data == "adm_points_settings")
def cb_adm_points_settings(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    edit(call,
        f" <b>إعدادات النقاط</b>\n\n"
        f" الهدية اليومية: <b>{db.get_config('daily_gift_points', '5')}</b>\n"
        f" الهدية الأسبوعية: <b>{db.get_config('weekly_gift_points', '50')}</b>\n"
        f" الإحالة: <b>{db.get_config('referral_points', '50')}</b>\n"
        f" سعر العضو: <b>{db.get_config('points_per_member', '1')}</b>",
        kb.admin_points_settings_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_daily_pts")
def _x1(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_set_daily_pts")
    edit(call, " أرسل عدد نقاط الهدية اليومية:", kb.back_keyboard("adm_points_settings"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_weekly_pts")
def _x1b(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_set_weekly_pts")
    edit(call, " أرسل عدد نقاط الهدية الأسبوعية:", kb.back_keyboard("adm_points_settings"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_ref_pts")
def _x2(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_set_ref_pts")
    edit(call, " أرسل عدد نقاط الإحالة:", kb.back_keyboard("adm_points_settings"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_set_member_price")
def _x3(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_set_member_price")
    edit(call, " أرسل سعر العضو بالنقاط:", kb.back_keyboard("adm_points_settings"))

#  إحصائيات / إذاعة / شحن / تحديثات / دعم 
@bot.callback_query_handler(func=lambda c: c.data == "adm_stats")
def cb_adm_stats(call):
    if not is_admin(call.from_user.id): return
    smm_bal = smm.get_balance()
    total_u = db.get_users_count()
    total_o, today_o, revenue, today_rev, total_pts = db.get_orders_stats()
    ref_count = db.get_referral_log_count()
    edit(call,
        f" <b>الإحصائيات</b>\n\n"
        f" المستخدمون: <b>{total_u}</b>\n"
        f" الطلبات: <b>{total_o}</b> (اليوم {today_o})\n"
        f" نقاط مستخدمة: <b>{total_pts:,}</b>\n"
        f" الأرباح: <b>{revenue:.2f}$</b> (اليوم {today_rev:.2f}$)\n"
        f" الإحالات: <b>{ref_count}</b>\n"
        f" SMMParty: <b>{smm_bal:.2f}$</b>",
        kb.back_keyboard("adm_back"))

# ══════════════════════════════════════════════════════════════════
#   نظام الإذاعة المتطور ✨  (Advanced Broadcast System V2)
#   ✅ إذاعة للمستخدمين + جميع القنوات التي البوت أدمن فيها
#   ✅ اختيار الهدف: الكل / مستخدمون / قنوات فقط
#   ✅ إذاعة عادية + إذاعة مع زر + إذاعة مجدولة
#   ✅ تقدم حي مع شريط تحميل
#   ✅ threading لعدم تجميد البوت
#   ✅ إحصائيات تفصيلية بعد الإرسال
# ══════════════════════════════════════════════════════════════════

def _bcast_progress_bar(done: int, total: int, width: int = 12) -> str:
    """شريط تقدم نصي جميل"""
    if total == 0:
        return "░" * width
    filled = int(width * done / total)
    bar = "█" * filled + "░" * (width - filled)
    pct = int(100 * done / total)
    return f"{bar} {pct}%"

def _bcast_get_all_channels_full():
    """
    يجمع كل القنوات من جميع المصادر ويتحقق أن البوت أدمن فيها.
    يرجع قائمة من (chat_id, title).
    """
    all_ids = {}   # chat_id -> title

    # ① الجداول المخزّنة
    try:
        for c in db.get_mandatory_channels():
            all_ids[str(c["channel_id"])] = c.get("channel_name", "")
    except Exception: pass
    try:
        for c in db.get_points_channels():
            all_ids[str(c["channel_id"])] = c.get("channel_name", "")
    except Exception: pass
    try:
        for c in db.get_order_channels():
            all_ids[str(c["channel_id"])] = c.get("channel_name", "")
    except Exception: pass

    # ② القنوات المكتشفة تلقائياً (لما البوت يُضاف كأدمن)
    try:
        conn_d = db.get_conn()
        rows = conn_d.execute("SELECT chat_id, chat_title FROM discovered_channels").fetchall()
        conn_d.close()
        for r in rows:
            cid = str(r["chat_id"])
            if cid not in all_ids:
                all_ids[cid] = r.get("chat_title", "")
    except Exception: pass

    # ③ إعدادات config (updates_channel, bot_channel, orders_channel)
    for key in ("updates_channel", "bot_channel", "orders_channel"):
        try:
            val = db.get_config(key, "")
            if val:
                parts = [p.strip() for p in val.split("|")]
                for p in parts:
                    if p.startswith("@") or p.lstrip("-").isdigit():
                        if p not in all_ids:
                            all_ids[p] = p
                    elif p.startswith("https://t.me/"):
                        uname = "@" + p.split("https://t.me/")[-1].split("/")[0]
                        if uname not in all_ids:
                            all_ids[uname] = uname
        except Exception: pass

    # ④ التحقق الفعلي أن البوت أدمن
    bot_id = bot.get_me().id
    verified = []
    for ch_id, title in all_ids.items():
        if not ch_id:
            continue
        try:
            member = bot.get_chat_member(ch_id, bot_id)
            if member.status in ("administrator", "creator"):
                # جلب الاسم الحقيقي لو ما كان موجود
                if not title:
                    try:
                        chat_info = bot.get_chat(ch_id)
                        title = chat_info.title or str(ch_id)
                    except Exception:
                        title = str(ch_id)
                verified.append((ch_id, title))
        except Exception:
            pass
    return verified


def _run_broadcast(admin_id: int, progress_msg_id: int, progress_chat_id: int,
                   target: str, msg_chat_id: int, msg_id: int,
                   btn_text: str = None, btn_url: str = None, brd_text: str = None,
                   brd_msg_obj=None):
    """
    ينفذ الإذاعة في thread مستقل مع تحديث تقدم حي.
    target: 'all' | 'users' | 'channels'
    """
    users_ok = users_fail = 0
    ch_ok = ch_fail = 0
    channels_list = []

    # ── تجهيز الزر (لو موجود) ──
    m_btn = None
    if btn_text and btn_url:
        m_btn = InlineKeyboardMarkup()
        m_btn.row(InlineKeyboardButton(btn_text, url=btn_url))

    def _send_one(dest):
        """
        يبعت الرسالة للوجهة حسب نوعها (نص/صورة/فيديو/ملف/صوت).
        يستخدم brd_msg_obj لو موجود (الأضمن)، وإلا copy_message.
        """
        try:
            if brd_text:
                # إذاعة نص مع زر
                bot.send_message(dest, brd_text, reply_markup=m_btn, parse_mode="HTML")
            elif brd_msg_obj is not None:
                # إعادة إرسال حسب نوع الرسالة مباشرةً — يضمن الوصول للقنوات
                ct = brd_msg_obj.content_type
                cap = brd_msg_obj.caption or ""
                if ct == "text":
                    bot.send_message(dest, brd_msg_obj.text or "", reply_markup=m_btn, parse_mode="HTML")
                elif ct == "photo":
                    bot.send_photo(dest, brd_msg_obj.photo[-1].file_id,
                                   caption=cap, reply_markup=m_btn, parse_mode="HTML")
                elif ct == "video":
                    bot.send_video(dest, brd_msg_obj.video.file_id,
                                   caption=cap, reply_markup=m_btn, parse_mode="HTML")
                elif ct == "document":
                    bot.send_document(dest, brd_msg_obj.document.file_id,
                                      caption=cap, reply_markup=m_btn, parse_mode="HTML")
                elif ct == "audio":
                    bot.send_audio(dest, brd_msg_obj.audio.file_id,
                                   caption=cap, reply_markup=m_btn, parse_mode="HTML")
                elif ct == "voice":
                    bot.send_voice(dest, brd_msg_obj.voice.file_id,
                                   caption=cap, reply_markup=m_btn, parse_mode="HTML")
                elif ct == "sticker":
                    bot.send_sticker(dest, brd_msg_obj.sticker.file_id)
                elif ct == "animation":
                    bot.send_animation(dest, brd_msg_obj.animation.file_id,
                                       caption=cap, reply_markup=m_btn, parse_mode="HTML")
                else:
                    # fallback للأنواع غير المعروفة
                    bot.copy_message(dest, msg_chat_id, msg_id, reply_markup=m_btn)
            else:
                bot.copy_message(dest, msg_chat_id, msg_id, reply_markup=m_btn)
            return True
        except Exception:
            return False

    def _update_progress(label, done, total, ch_d=0, ch_t=0):
        try:
            txt = (
                f"📡 <b>جاري الإذاعة...</b>\n\n"
                f"<b>{label}</b>\n"
                f"<code>{_bcast_progress_bar(done, total)}</code>\n"
                f"✅ نجح: <b>{done}</b>  ❌ فشل: <b>{total - done}</b>  📊 إجمالي: <b>{total}</b>"
            )
            if ch_t:
                txt += (
                    f"\n\n📢 <b>القنوات</b>\n"
                    f"<code>{_bcast_progress_bar(ch_d, ch_t)}</code>\n"
                    f"✅ نجح: <b>{ch_d}</b>  إجمالي: <b>{ch_t}</b>"
                )
            bot.edit_message_text(txt, progress_chat_id, progress_msg_id)
        except Exception:
            pass

    # ── إذاعة المستخدمين ──
    if target in ("all", "users"):
        users = db.get_all_users()
        total_u = len(users)
        last_update = 0
        for i, u in enumerate(users):
            ok = _send_one(u["tg_id"])
            if ok:
                users_ok += 1
            else:
                users_fail += 1
            # تحديث كل 30 رسالة أو في النهاية
            if i - last_update >= 30 or i == total_u - 1:
                _update_progress("👥 المستخدمون", users_ok, total_u)
                last_update = i
            time.sleep(0.033)  # ~30 msg/sec ضمن حدود تيليغرام

    # ── إذاعة القنوات ──
    if target in ("all", "channels"):
        channels_list = _bcast_get_all_channels_full()
        total_ch = len(channels_list)
        for i, (ch_id, ch_title) in enumerate(channels_list):
            ok = _send_one(ch_id)
            if ok:
                ch_ok += 1
            else:
                ch_fail += 1
            if i % 5 == 0 or i == total_ch - 1:
                _update_progress(
                    "👥 المستخدمون", users_ok, len(db.get_all_users()) if target == "all" else 0,
                    ch_ok, total_ch
                )
            time.sleep(0.05)

    # ── رسالة النتيجة النهائية ──
    total_u_count = len(db.get_all_users()) if target in ("all", "users") else 0
    ch_names_preview = "\n".join(
        f"  • {t or cid}" for cid, t in channels_list[:8]
    ) if channels_list else "—"
    if len(channels_list) > 8:
        ch_names_preview += f"\n  ... و {len(channels_list)-8} قناة أخرى"

    result_txt = (
        f"✅ <b>اكتملت الإذاعة!</b>\n"
        f"{'─'*28}\n"
    )
    if target in ("all", "users"):
        result_txt += (
            f"👤 <b>المستخدمون</b>\n"
            f"   ✅ وصلت: <b>{users_ok}</b>  ❌ فشلت: <b>{users_fail}</b>  📊 إجمالي: <b>{total_u_count}</b>\n\n"
        )
    if target in ("all", "channels"):
        result_txt += (
            f"📢 <b>القنوات</b>\n"
            f"   ✅ وصلت: <b>{ch_ok}</b>  ❌ فشلت: <b>{ch_fail}</b>  📊 إجمالي: <b>{len(channels_list)}</b>\n"
            f"<blockquote>{ch_names_preview}</blockquote>\n"
        )
    result_txt += f"\n⏱ انتهت الإذاعة"

    try:
        bot.edit_message_text(result_txt, progress_chat_id, progress_msg_id,
                              reply_markup=InlineKeyboardMarkup([[
                                  InlineKeyboardButton("📡 إذاعة جديدة", callback_data="adm_broadcast"),
                                  InlineKeyboardButton("🏠 لوحة الأدمن", callback_data="adm_back"),
                              ]]))
    except Exception:
        bot.send_message(progress_chat_id, result_txt)


# ── لوحة الإذاعة الرئيسية ──
@bot.callback_query_handler(func=lambda c: c.data == "adm_broadcast")
def cb_adm_broadcast(call):
    if not is_admin(call.from_user.id): return
    clear_state(call.from_user.id)
    m = InlineKeyboardMarkup()
    m.row(
        InlineKeyboardButton("📝 إذاعة نص/صورة/فيديو", callback_data="adm_bcast_type_simple"),
    )
    m.row(
        InlineKeyboardButton("🔗 إذاعة مع زر رابط", callback_data="adm_bcast_type_btn"),
    )
    m.row(
        InlineKeyboardButton("📊 القنوات المكتشفة", callback_data="adm_bcast_stats"),
        InlineKeyboardButton("➕ إضافة قناة يدوياً", callback_data="adm_bcast_add_channel"),
    )
    m.row(
        InlineKeyboardButton("🔍 مسح وإضافة القنوات تلقائياً", callback_data="adm_bcast_scan_channels"),
    )
    m.row(InlineKeyboardButton("🔙 رجوع", callback_data="adm_back"))
    total_u = db.get_users_count()
    channels = _bcast_get_all_channels_full()
    total_ch = len(channels)
    edit(call,
        f"📡 <b>نظام الإذاعة المتطور</b>\n"
        f"{'─'*28}\n"
        f"👥 المستخدمون: <b>{total_u:,}</b>\n"
        f"📢 القنوات المتاحة للإذاعة: <b>{total_ch}</b>\n\n"
        f"{'⚠️ <b>القنوات = 0</b> — اضغط 🔍 مسح لإضافة قنواتك' if total_ch == 0 else 'اختر نوع الإذاعة أو أضف قنوات:'}",
        m)


# ── مسح القنوات تلقائياً من orders المكتملة والمصادر الأخرى ──
@bot.callback_query_handler(func=lambda c: c.data == "adm_bcast_scan_channels")
def cb_adm_bcast_scan_channels(call):
    if not is_admin(call.from_user.id): return
    bot.answer_callback_query(call.id, "⏳ جاري المسح...")
    edit(call,
        "🔍 <b>جاري مسح القنوات...</b>\n\n"
        "يتحقق من كل القنوات في قاعدة البيانات\n"
        "⏳ يرجى الانتظار لثوانٍ...",
        None)

    added = 0
    already = 0
    failed = 0
    bot_id = bot.get_me().id

    # ① جمع كل IDs من الطلبات المكتملة (تمويلات قنوات)
    candidate_ids = set()
    try:
        conn_s = db.get_conn()
        # من الطلبات — حقل link يحتوي على @username أو https://t.me/...
        rows = conn_s.execute(
            "SELECT DISTINCT link FROM orders WHERE status IN ('completed','partial','processing','inprogress')"
        ).fetchall()
        for r in rows:
            lnk = (r["link"] or "").strip()
            if lnk.startswith("@"):
                candidate_ids.add(lnk)
            elif lnk.startswith("https://t.me/"):
                uname = "@" + lnk.split("https://t.me/")[-1].split("/")[0]
                if uname != "@":
                    candidate_ids.add(uname)
        conn_s.close()
    except Exception: pass

    # ② من جداول القنوات المخزّنة
    try:
        for c in db.get_mandatory_channels():
            candidate_ids.add(str(c["channel_id"]))
    except Exception: pass
    try:
        for c in db.get_points_channels():
            candidate_ids.add(str(c["channel_id"]))
    except Exception: pass
    try:
        for c in db.get_order_channels():
            candidate_ids.add(str(c["channel_id"]))
    except Exception: pass

    # ③ التحقق والإضافة
    conn_dc = db.get_conn()
    try:
        conn_dc.execute("""
            CREATE TABLE IF NOT EXISTS discovered_channels (
                chat_id    TEXT PRIMARY KEY,
                chat_title TEXT DEFAULT '',
                chat_type  TEXT DEFAULT '',
                added_at   TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn_dc.commit()
    except Exception: pass

    for cid in candidate_ids:
        if not cid or cid in ("@", ""):
            continue
        try:
            member = bot.get_chat_member(cid, bot_id)
            if member.status in ("administrator", "creator"):
                try:
                    chat_info = bot.get_chat(cid)
                    title = chat_info.title or str(cid)
                    chat_type = chat_info.type or "channel"
                    real_id = str(chat_info.id)
                except Exception:
                    title = str(cid)
                    chat_type = "channel"
                    real_id = str(cid)
                try:
                    existing = conn_dc.execute(
                        "SELECT chat_id FROM discovered_channels WHERE chat_id=?", (real_id,)
                    ).fetchone()
                    if existing:
                        already += 1
                    else:
                        conn_dc.execute(
                            "INSERT OR IGNORE INTO discovered_channels(chat_id, chat_title, chat_type) VALUES(?,?,?)",
                            (real_id, title, chat_type)
                        )
                        conn_dc.commit()
                        added += 1
                except Exception:
                    already += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    conn_dc.close()

    # النتيجة
    channels_now = _bcast_get_all_channels_full()
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton("➕ إضافة قناة يدوياً", callback_data="adm_bcast_add_channel"))
    m.row(InlineKeyboardButton("🔙 رجوع للإذاعة", callback_data="adm_broadcast"))
    try:
        bot.edit_message_text(
            f"✅ <b>اكتمل المسح!</b>\n"
            f"{'─'*28}\n"
            f"➕ أُضيف جديد: <b>{added}</b>\n"
            f"✔️ موجود مسبقاً: <b>{already}</b>\n"
            f"❌ البوت مش أدمن: <b>{failed}</b>\n"
            f"{'─'*28}\n"
            f"📢 إجمالي القنوات الآن: <b>{len(channels_now)}</b>\n\n"
            f"{'⚠️ لو قناتك مش ظاهرة — استخدم ➕ إضافة يدوياً' if len(channels_now) == 0 else '✅ يمكنك الإذاعة الآن!'}",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=m
        )
    except Exception:
        bot.send_message(call.message.chat.id,
            f"✅ مسح اكتمل — أُضيف {added} قناة جديدة، الإجمالي: {len(channels_now)}",
            reply_markup=m)


# ── إضافة قناة يدوياً ──
@bot.callback_query_handler(func=lambda c: c.data == "adm_bcast_add_channel")
def cb_adm_bcast_add_channel(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_bcast_manual_channel")
    edit(call,
        "➕ <b>إضافة قناة يدوياً</b>\n"
        f"{'─'*28}\n"
        "أرسل <b>يوزرنيم القناة</b> أو <b>ID</b> أو <b>رابطها</b>:\n\n"
        "مثال:\n"
        "<code>@mychannel</code>\n"
        "<code>-100123456789</code>\n"
        "<code>https://t.me/mychannel</code>\n\n"
        "<i>يمكن إرسال أكثر من قناة — كل قناة في سطر</i>",
        InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast")]]))


# ── معالجة إضافة القناة اليدوية في message handler ──
# (يُضاف في msg_admin_states تحت state جديد)


# ── اختيار الهدف (target) ──
def _bcast_target_keyboard(bcast_type: str):
    m = InlineKeyboardMarkup()
    m.row(
        InlineKeyboardButton("👥+📢 الكل (مستخدمون + قنوات)", callback_data=f"adm_bcast_target_{bcast_type}_all"),
    )
    m.row(
        InlineKeyboardButton("👥 مستخدمون فقط", callback_data=f"adm_bcast_target_{bcast_type}_users"),
        InlineKeyboardButton("📢 قنوات فقط",    callback_data=f"adm_bcast_target_{bcast_type}_channels"),
    )
    m.row(InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast"))
    return m


@bot.callback_query_handler(func=lambda c: c.data == "adm_bcast_type_simple")
def cb_adm_bcast_type_simple(call):
    if not is_admin(call.from_user.id): return
    edit(call,
        "📡 <b>إذاعة عادية</b>\n\n"
        "اختر الهدف:",
        _bcast_target_keyboard("simple"))


@bot.callback_query_handler(func=lambda c: c.data == "adm_bcast_type_btn")
def cb_adm_bcast_type_btn(call):
    if not is_admin(call.from_user.id): return
    edit(call,
        "🔗 <b>إذاعة مع زر رابط</b>\n\n"
        "اختر الهدف:",
        _bcast_target_keyboard("btn"))


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_bcast_target_"))
def cb_adm_bcast_target(call):
    if not is_admin(call.from_user.id): return
    # adm_bcast_target_{type}_{target}
    parts = call.data[len("adm_bcast_target_"):].rsplit("_", 1)
    if len(parts) != 2:
        bot.answer_callback_query(call.id, "خطأ"); return
    bcast_type, target = parts  # simple|btn , all|users|channels

    target_label = {"all": "👥+📢 الكل", "users": "👥 المستخدمون", "channels": "📢 القنوات"}.get(target, target)

    if bcast_type == "simple":
        set_state(call.from_user.id, "adm_bcast_msg_simple", target=target)
        edit(call,
            f"📡 <b>إذاعة عادية</b>  ←  {target_label}\n\n"
            f"أرسل الرسالة (نص / صورة / فيديو / ملف / صوت):\n\n"
            f"<i>سيتم إرسالها كما هي بكل تنسيقها</i>",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast")]]))

    elif bcast_type == "btn":
        set_state(call.from_user.id, "adm_bcast_btn1_text", target=target)
        edit(call,
            f"🔗 <b>إذاعة مع زر</b>  ←  {target_label}\n\n"
            f"<b>الخطوة 1/3:</b> أرسل <b>نص الزر</b>:\n"
            f"مثال: <code>🔥 اشترك الآن</code>",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast")]]))


# ── إحصائيات سريعة ──
@bot.callback_query_handler(func=lambda c: c.data == "adm_bcast_stats")
def cb_adm_bcast_stats(call):
    if not is_admin(call.from_user.id): return
    bot.answer_callback_query(call.id, "⏳ جاري الفحص...")
    channels = _bcast_get_all_channels_full()
    total_u = db.get_users_count()
    lines = [f"📊 <b>إحصائيات الإذاعة</b>\n{'─'*28}",
             f"👥 المستخدمون: <b>{total_u:,}</b>",
             f"📢 القنوات المتاحة: <b>{len(channels)}</b>\n"]
    for ch_id, title in channels[:20]:
        lines.append(f"  • <code>{ch_id}</code>  {title}")
    if len(channels) > 20:
        lines.append(f"  ... و {len(channels)-20} قناة أخرى")
    m = InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast")]])
    edit(call, "\n".join(lines), m)


# ── قديمة للتوافق (adm_broadcast_simple / adm_broadcast_with_btn) ──
@bot.callback_query_handler(func=lambda c: c.data == "adm_broadcast_simple")
def cb_adm_broadcast_simple(call):
    if not is_admin(call.from_user.id): return
    cb_adm_bcast_type_simple(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_broadcast_with_btn")
def cb_adm_broadcast_with_btn(call):
    if not is_admin(call.from_user.id): return
    cb_adm_bcast_type_btn(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_topup")
def cb_adm_topup(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_topup_id")
    edit(call, " أرسل ID المستخدم:", kb.back_keyboard("adm_back"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_updates_ch")
def cb_adm_updates_ch(call):
    if not is_admin(call.from_user.id): return
    cur = db.get_config("updates_channel", "")
    set_state(call.from_user.id, "adm_set_updates_ch")
    edit(call, f" الحالية: <code>{cur}</code>\n\nأرسل الرابط الجديد:",
         kb.back_keyboard("adm_back"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_bot_channel")
def cb_adm_bot_channel(call):
    if not is_admin(call.from_user.id): return
    cur = db.get_config("bot_channel", "")
    set_state(call.from_user.id, "adm_set_bot_channel")
    edit(call,
        f" <b>قناة البوت الرئيسية</b>\n\n"
        f"الحالية: <code>{cur}</code>\n\n"
        f"أرسل رابط القناة (مثال: https://t.me/mychannel)\n"
        f"أو أرسل <code>-</code> لإزالتها",
        kb.back_keyboard("adm_back"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_support")
def cb_adm_support(call):
    if not is_admin(call.from_user.id): return
    cur = db.get_config("support_username", "@support")
    set_state(call.from_user.id, "adm_set_support")
    edit(call, f" الحالي: <code>{cur}</code>\n\nأرسل اليوزر الجديد:",
         kb.back_keyboard("adm_back"))

#  قنوات إجبارية 
@bot.callback_query_handler(func=lambda c: c.data == "adm_mandatory")
def cb_adm_mandatory(call):
    if not is_admin(call.from_user.id): return
    channels = db.get_mandatory_channels()
    text = f" <b>قنوات الاشتراك الإجباري</b>\n\nعدد القنوات: <b>{len(channels)}</b>\n\n"
    if channels:
        for ch in channels:
            t = ch["target_members"] if "target_members" in ch.keys() else 0
            cm = ch["current_members"] if "current_members" in ch.keys() else 0
            text += f" {ch['channel_name']}"
            if t > 0:
                text += f" ({cm}/{t} عضو)"
            text += "\n"
    edit(call, text, kb.admin_mandatory_keyboard(channels))

@bot.callback_query_handler(func=lambda c: c.data == "adm_add_mand")
def cb_adm_add_mand(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_add_mand_step1")
    edit(call,
        " <b>إضافة قناة إجبارية  مساعد سهل</b>\n\n"
        "<b>الخطوة 1/4:</b>\n"
        "أرسل معرف القناة (مثال: <code>@mychannel</code> أو <code>-1001234567890</code>)\n\n"
        "<i> يجب أن يكون البوت أدمن في القناة</i>",
        kb.back_keyboard("adm_mandatory"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_mand_"))
def cb_adm_del_mand(call):
    if not is_admin(call.from_user.id): return
    ch_id = call.data.replace("adm_del_mand_", "")
    db.remove_mandatory_channel(ch_id)
    bot.answer_callback_query(call.id, " تم الحذف")
    cb_adm_mandatory(call)

#  قنوات النقاط 
@bot.callback_query_handler(func=lambda c: c.data == "adm_points_ch")
def cb_adm_points_ch(call):
    if not is_admin(call.from_user.id): return
    channels = db.get_points_channels()
    edit(call, f" <b>قنوات النقاط</b>\n\nعدد: <b>{len(channels)}</b>",
         kb.admin_points_channels_keyboard(channels))

@bot.callback_query_handler(func=lambda c: c.data == "adm_add_ptch")
def cb_adm_add_ptch(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_add_ptch_data")
    edit(call,
        " <b>إضافة قناة نقاط</b>\n\n"
        "<code>channel_id|الاسم|https://t.me/channel|النقاط</code>",
        kb.back_keyboard("adm_points_ch"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_ptch_"))
def cb_adm_del_ptch(call):
    if not is_admin(call.from_user.id): return
    ch_id = call.data.replace("adm_del_ptch_", "")
    db.remove_points_channel(ch_id)
    bot.answer_callback_query(call.id, " تم الحذف")
    cb_adm_points_ch(call)

#  المستخدمون 
@bot.callback_query_handler(func=lambda c: c.data == "adm_users")
def cb_adm_users(call):
    if not is_admin(call.from_user.id): return
    edit(call, f" <b>إدارة المستخدمين</b>\n\nالإجمالي: <b>{db.get_users_count()}</b>",
         kb.admin_users_keyboard())

@bot.callback_query_handler(func=lambda c: c.data == "adm_search_user")
def cb_adm_search_user(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_search_user")
    edit(call, " أرسل ID المستخدم:", kb.back_keyboard("adm_users"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_ban_") or c.data.startswith("adm_unban_"))
def cb_adm_ban(call):
    if not is_admin(call.from_user.id): return
    parts = call.data.split("_")
    action = parts[1]; target = int(parts[2])
    db.update_user(target, is_banned=1 if action == "ban" else 0)
    bot.answer_callback_query(call.id, " تم")
    #  إشعار المستخدم 
    try:
        if action == "ban":
            bot.send_message(target,
                " <b>تم حظرك من استخدام البوت.</b>\n\n"
                "للاستفسار تواصل مع الدعم.",
                parse_mode="HTML")
        else:
            bot.send_message(target,
                " <b>تم رفع الحظر عنك!</b>\n\n"
                "يمكنك الآن استخدام البوت مجدداً. ",
                parse_mode="HTML")
    except Exception: pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_add_pts_") or c.data.startswith("adm_sub_pts_"))
def cb_adm_pts_action(call):
    if not is_admin(call.from_user.id): return
    parts = call.data.split("_")
    action = "add" if parts[1] == "add" else "sub"
    target = int(parts[3])
    set_state(call.from_user.id, f"adm_{action}_points", target_id=target)
    edit(call, f" أرسل عدد النقاط ({'إضافة' if action == 'add' else 'خصم'}):",
         kb.back_keyboard("adm_back"))

#  روابط الدعوة 
@bot.callback_query_handler(func=lambda c: c.data == "adm_invite_links")
def cb_adm_invite_links(call):
    if not is_admin(call.from_user.id): return
    links = db.get_all_invite_links()
    edit(call,
        f" <b>أكواد الدعوة</b>\n\nعدد: <b>{len(links)}</b>",
        kb.admin_invite_links_keyboard(links))

@bot.callback_query_handler(func=lambda c: c.data == "adm_create_invite")
def cb_adm_create_invite(call):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_create_invite")
    edit(call,
        " <b>كود دعوة جديد</b>\n\n"
        "<code>الكود|النقاط|الحد_الأقصى</code>\n\n"
        "<i>الحد=0 يعني غير محدود</i>",
        kb.back_keyboard("adm_invite_links"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_invite_"))
def cb_adm_del_invite(call):
    if not is_admin(call.from_user.id): return
    code = call.data.replace("adm_del_invite_", "")
    db.delete_invite_link(code)
    bot.answer_callback_query(call.id, " تم الحذف")
    cb_adm_invite_links(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_referral_log")
def cb_adm_referral_log(call):
    if not is_admin(call.from_user.id): return
    cnt = db.get_referral_log_count()
    edit(call, f" <b>سجل الإحالات</b>\n\nالإجمالي: <b>{cnt}</b> إحالة",
         kb.back_keyboard("adm_back"))

# 
#   إدارة الأدمنية (ديناميكي)
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_manage_admins")
def cb_adm_manage_admins(call: CallbackQuery):
    if call.from_user.id not in config.ADMIN_IDS: return  # فقط الأدمن الأصلي
    admins = db.get_dynamic_admins()
    text = (
        f" <b>إدارة الأدمنية</b>\n\n"
        f"الأدمنية الثابتون (في config): <b>{len(config.ADMIN_IDS)}</b>\n"
        f"الأدمنية المضافون ديناميكياً: <b>{len(admins)}</b>\n\n"
        f"<i>الأدمنية المضافون هنا يملكون نفس صلاحيات الأدمن الكامل.</i>"
    )
    edit(call, text, kb.admin_manage_admins_keyboard(admins))

@bot.callback_query_handler(func=lambda c: c.data == "adm_add_admin")
def cb_adm_add_admin(call: CallbackQuery):
    if call.from_user.id not in config.ADMIN_IDS: return
    set_state(call.from_user.id, "adm_add_admin_id")
    edit(call,
        " <b>إضافة أدمن جديد</b>\n\n"
        "أرسل <b>ID التليجرام</b> للمستخدم المراد ترقيته أدمن:\n\n"
        "<i> يمكن إضافة ملاحظة اختيارية:\n"
        "<code>ID|ملاحظة</code></i>",
        kb.back_keyboard("adm_manage_admins"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_del_admin_"))
def cb_adm_del_admin(call: CallbackQuery):
    if call.from_user.id not in config.ADMIN_IDS: return
    tg_id = int(call.data.split("_")[-1])
    db.remove_dynamic_admin(tg_id)
    bot.answer_callback_query(call.id, " تم حذف الأدمن")
    try:
        bot.send_message(tg_id,
            " <b>تم إلغاء صلاحيات الأدمن الخاصة بك.</b>",
            parse_mode="HTML")
    except Exception: pass
    cb_adm_manage_admins(call)

# 
#   إدارة التمويلات المكتملة (أدمن)
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_fundings")
def cb_adm_fundings(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    fundings = db.get_showcase_fundings(only_active=False)
    edit(call,
        f" <b>إدارة التمويلات المكتملة</b>\n\n"
        f"عدد التمويلات: <b>{len(fundings)}</b>\n\n"
        f"<i>اضغط على تمويل لتفعيل/تعطيله   للحذف</i>",
        kb.admin_fundings_keyboard(fundings))

@bot.callback_query_handler(func=lambda c: c.data == "adm_funding_add")
def cb_adm_funding_add(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_add_funding")
    edit(call,
        " <b>إضافة تمويل مكتمل</b>\n\n"
        "أرسل البيانات بهذا الشكل:\n"
        "<code>العنوان|الإيموجي|عدد_الأعضاء|وصف (اختياري)|رابط_القناة (اختياري)</code>\n\n"
        "<b>أمثلة:</b>\n"
        "<code>قناة MCV رسمية||50000|تم تمويلها في 3 أيام|https://t.me/channel</code>\n"
        "<code>جروب المبدعين||10000</code>",
        kb.back_keyboard("adm_fundings"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_funding_tog_"))
def cb_adm_funding_tog(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    fid = int(call.data.split("_")[-1])
    db.toggle_completed_funding(fid)
    bot.answer_callback_query(call.id, " تم التبديل")
    cb_adm_fundings(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_funding_del_"))
def cb_adm_funding_del(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    fid = int(call.data.split("_")[-1])
    db.delete_completed_funding(fid)
    bot.answer_callback_query(call.id, " تم الحذف")
    cb_adm_fundings(call)

# 
#   إدارة عجلة الحظ (للأدمن)
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_wheel")
def cb_adm_wheel(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    prizes = db.get_wheel_prizes(only_active=False)
    total_w = sum(float(p["weight"]) for p in prizes if p["is_active"])

    txt = " <b>إدارة عجلة الحظ</b>\n\n"
    txt += f"عدد الجوائز: <b>{len(prizes)}</b>\n"
    txt += f"مجموع الأوزان (المُفعّل): <b>{total_w:g}</b>\n"
    txt += "\n"
    if prizes:
        txt += "<b>الجوائز الحالية:</b>\n"
        for p in prizes:
            status = "" if p["is_active"] else ""
            chance = (float(p["weight"]) / total_w * 100) if (p["is_active"] and total_w > 0) else 0
            txt += (f"{status} {p['emoji']} <b>{p['points']}</b> نقطة "
                    f"| وزن: {p['weight']:g} | نسبة: {chance:.1f}%\n")
    else:
        txt += "<i>لا توجد جوائز بعد</i>\n"

    m = InlineKeyboardMarkup()
    for p in prizes:
        st = "" if p["is_active"] else ""
        m.row(
            kb._btn(f"{st} {p['emoji']} {p['points']}pt", f"adm_wheel_tog_{p['id']}", style="primary"),
            kb._btn("", f"adm_wheel_del_{p['id']}", style="danger"),
        )
    m.row(kb._btn(" إضافة جائزة", "adm_wheel_add", style="success"))
    m.row(kb._btn("رجوع", "adm_back", style="danger"))
    edit(call, txt, m)

@bot.callback_query_handler(func=lambda c: c.data == "adm_wheel_add")
def cb_adm_wheel_add(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_wheel_add")
    edit(call,
        " <b>إضافة جائزة لعجلة الحظ</b>\n\n"
        "أرسل بيانات الجائزة بهذا الشكل:\n\n"
        "<code>النقاط|الوزن|الإيموجي</code>\n\n"
        "<b>أمثلة:</b>\n"
        " <code>50|10|</code>\n"
        " <code>500|1.5|</code>\n\n"
        "<i> الوزن = احتمالية الظهور (كل ما زاد، زادت فرصة ظهور الجائزة)\n"
        "خلي الجوايز الكبيرة وزنها أقل عشان ما تطلعش كتير</i>",
        kb.back_keyboard("adm_wheel"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_wheel_tog_"))
def cb_adm_wheel_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    pid = int(call.data.split("_")[-1])
    db.toggle_wheel_prize(pid)
    bot.answer_callback_query(call.id, " تم التبديل")
    cb_adm_wheel(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_wheel_del_"))
def cb_adm_wheel_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    pid = int(call.data.split("_")[-1])
    db.delete_wheel_prize(pid)
    bot.answer_callback_query(call.id, " تم الحذف")
    cb_adm_wheel(call)

# 
#   إدارة روابط الهدايا (أدمن)
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_gift_links")
def cb_adm_gift_links(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    links = db.get_all_gift_links()
    text = f" <b>روابط الهدايا</b> ({len(links)} رابط)\n\n"
    if not links:
        text += "<i>لا توجد روابط هدايا حتى الآن.</i>"
    m = InlineKeyboardMarkup()
    for gl in links:
        st = "✅" if gl["is_active"] else "⏸"
        uses = "∞" if gl["max_claims"] == -1 else f"{gl['current_claims']}/{gl['max_claims']}"
        note_txt = f" ({gl['note']})" if gl.get("note") else ""
        bu = config.BOT_USERNAME.lstrip("@")
        gift_url = f"https://t.me/{bu}?start=gift_{gl['code']}"
        m.row(
            kb._btn(f"🎁 +{gl['points']}نق ({uses}){note_txt}", url=gift_url, style="success"),
            kb._btn(f"{st} تفاصيل", f"adm_gift_view_{gl['id']}", style="primary"),
        )
    m.row(kb._btn("إنشاء رابط هدية", "adm_create_gift_link", style="success"))
    m.row(kb._btn("رجوع", "adm_back", style="danger"))
    edit(call, text, m)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_gift_view_"))
def cb_adm_gift_view(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    gid = int(call.data.split("_")[-1])
    conn = db.get_conn()
    gl = conn.execute("SELECT * FROM gift_links WHERE id=?", (gid,)).fetchone()
    conn.close()
    if not gl:
        bot.answer_callback_query(call.id, " الرابط غير موجود"); return
    st = "✅ نشط" if gl["is_active"] else "⏸ متوقف"
    uses = "غير محدود ♾" if gl["max_claims"] == -1 else f"{gl['current_claims']}/{gl['max_claims']}"
    bu = config.BOT_USERNAME.lstrip("@")
    link_url = f"https://t.me/{bu}?start=gift_{gl['code']}"
    m = InlineKeyboardMarkup()
    m.row(kb._btn("🎁 افتح رابط الهدية الآن", url=link_url, style="success"))
    m.row(
        kb._btn("🔄 تفعيل / إيقاف", f"adm_gift_tog_{gid}", style="primary"),
        kb._btn("🗑 حذف", f"adm_gift_del_{gid}", style="danger"),
    )
    m.row(kb._btn("📤 إرسال للقناة", f"adm_gift_send_{gid}", style="success"))
    m.row(kb._btn("🔙 رجوع", "adm_gift_links", style="danger"))
    edit(call,
        f" <b>رابط الهدية #{gid}</b>\n\n"
        f"\n"
        f"  النقاط: <b>{gl['points']:,}</b>\n"
        f"  الحالة: {st}\n"
        f"  الاستخدامات: {uses}\n"
        f"  الملاحظة: {gl.get('note') or ''}\n"
        f"\n\n"
        f" <b>الرابط:</b>\n<code>{link_url}</code>", m)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_gift_tog_"))
def cb_adm_gift_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    gid = int(call.data.split("_")[-1])
    db.toggle_gift_link(gid)
    bot.answer_callback_query(call.id, " تم التبديل")
    call.data = f"adm_gift_view_{gid}"
    cb_adm_gift_view(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_gift_del_"))
def cb_adm_gift_delete(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    gid = int(call.data.split("_")[-1])
    db.delete_gift_link(gid)
    bot.answer_callback_query(call.id, " تم الحذف")
    call.data = "adm_gift_links"
    cb_adm_gift_links(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_gift_send_"))
def cb_adm_gift_send(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    gid = int(call.data.split("_")[-1])
    set_state(call.from_user.id, "adm_send_gift_to_channel", gid=gid)
    edit(call,
        " <b>إرسال الهدية للقناة</b>\n\n"
        "أرسل <b>يوزرنيم القناة</b> أو <b>معرفها</b>:\n\n"
        "<code>@mychannel</code>\n"
        "<code>-1001234567890</code>",
        kb.back_keyboard("adm_gift_links"))

@bot.callback_query_handler(func=lambda c: c.data == "adm_create_gift_link")
def cb_adm_create_gift_link(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_create_gift_link")
    edit(call,
        " <b>إنشاء رابط هدية جديد</b>\n\n"
        "أرسل بهذا الشكل:\n"
        "<code>النقاط|عدد_الاستخدامات|ملاحظة (اختياري)</code>\n\n"
        "<b>أمثلة:</b>\n"
        "<code>100|50|هدية عيد الفطر</code>\n"
        "<code>500|-1|غير محدود</code>",
        kb.back_keyboard("adm_gift_links"))

# ==========================================
#   دالة مساعدة: كل القنوات التي البوت أدمن فيها
# ==========================================
def _get_all_admin_channels():
    """
    تجمع كل القنوات من جميع الجداول (إجبارية + نقاط + طلبات + تحديثات + قناة البوت)
    ثم تتحقق أن البوت أدمن فعلاً في كل واحدة، وترجع القائمة النظيفة.
    """
    all_ids = set()

    # من الجداول المخزّنة في DB
    try:
        for c in db.get_mandatory_channels():
            all_ids.add(str(c["channel_id"]))
    except Exception: pass
    try:
        for c in db.get_points_channels():
            all_ids.add(str(c["channel_id"]))
    except Exception: pass
    try:
        for c in db.get_order_channels():
            all_ids.add(str(c["channel_id"]))
    except Exception: pass
    # القنوات المكتشفة تلقائياً (لما البوت يتضاف كأدمن)
    try:
        conn_disc = db.get_conn()
        rows = conn_disc.execute("SELECT chat_id FROM discovered_channels").fetchall()
        conn_disc.close()
        for r in rows:
            all_ids.add(str(r["chat_id"]))
    except Exception: pass

    # من إعدادات config (قناة التحديثات + قناة البوت)
    for key in ("updates_channel", "bot_channel", "orders_channel"):
        try:
            val = db.get_config(key, "")
            if val:
                # قناة البوت قد تكون بصيغة "url|اسم|url2|اسم2"
                parts = [p.strip() for p in val.split("|")]
                for p in parts:
                    if p.startswith("@") or p.lstrip("-").isdigit():
                        all_ids.add(p)
                    elif p.startswith("https://t.me/"):
                        username = "@" + p.split("https://t.me/")[-1].split("/")[0]
                        all_ids.add(username)
        except Exception: pass

    # تصفية: فقط القنوات التي البوت فيها أدمن فعلاً
    verified = []
    bot_id = bot.get_me().id
    for ch_id in all_ids:
        if not ch_id:
            continue
        try:
            member = bot.get_chat_member(ch_id, bot_id)
            if member.status in ("administrator", "creator"):
                verified.append(ch_id)
        except Exception:
            pass
    return verified

# 
#   تمويل قناة / جروب (اختيار النوع)
# 
def _start_fund_flow(call: CallbackQuery, fund_type: str):
    """تشغيل flow التمويل مع تحديد نوع المنصة"""
    ok, missing = sync_check_subscriptions(call.from_user.id)
    if not ok:
        edit(call, " <b>اشترك في القنوات أولاً:</b>",
             kb.subscribe_keyboard(missing, call.from_user.id))
        return
    service_id = db.get_config("service_id")
    if not service_id:
        edit(call, " <b>الخدمة غير متاحة حالياً.</b>", kb.back_keyboard())
        return
    service_name   = db.get_config("service_name", "تمويل قنوات وجروبات")
    pts_per_member = int(db.get_config("points_per_member", "1"))
    svc_min        = db.get_config("service_min", "10")
    svc_max        = db.get_config("service_max", "100000")
    user           = db.get_user(call.from_user.id)
    max_can        = user["points"] // pts_per_member if pts_per_member > 0 else 0
    type_label     = " قناة تليجرام" if fund_type == "channel" else " جروب تليجرام"
    set_state(call.from_user.id, "waiting_quantity",
              service_id=service_id, service_name=service_name,
              pts_per_member=pts_per_member, svc_min=svc_min, svc_max=svc_max,
              fund_type=fund_type)
    edit(call,
        f" ارسل عدد الاعضاء المراد تمويلهم او يمكنك الاختيار من الازرار \n\n"
        f"- ملاحضة : كل 1 عضو يساوي {pts_per_member} نقطه\n\n"
        f"- عدد نقاطك : {user['points']:,}",
        kb.fund_qty_keyboard(max_can, pts_per_member, svc_min))

@bot.callback_query_handler(func=lambda c: c.data == "fund_channel")
def cb_fund_channel(call: CallbackQuery):
    _start_fund_flow(call, "channel")

@bot.callback_query_handler(func=lambda c: c.data == "fund_group")
def cb_fund_group(call: CallbackQuery):
    _start_fund_flow(call, "group")

@bot.callback_query_handler(func=lambda c: c.data.startswith("fund_qty_"))
def cb_fund_qty(call: CallbackQuery):
    state = get_state(call.from_user.id)
    if state.get("state") != "waiting_quantity":
        bot.answer_callback_query(call.id, " انتهت الجلسة"); return
    qty = int(call.data.split("_")[-1])
    d = state["data"]
    svc_min = int(d.get("svc_min", 10))
    svc_max = int(d.get("svc_max", 100000))
    if qty < svc_min or qty > svc_max:
        bot.answer_callback_query(call.id, f" الكمية بين {svc_min:,} و {svc_max:,}!", show_alert=True); return
    fund_type = d.get("fund_type", "channel")
    set_state(call.from_user.id, "waiting_link", **d, qty=qty)
    ch_or_gr = "القناة" if fund_type == "channel" else "الجروب"
    edit(call,
        f" تم تسجيل العدد: <b>{qty:,}</b> عضو\n\n"
        f" <b>الخطوة 2/2  أرسل معرف {ch_or_gr}</b>\n\n"
        f"\n"
        f" 1⃣ أضف البوت إلى {ch_or_gr}\n"
        f" 2⃣ رقّه إلى مشرف وأعطه صلاحية <b>دعوة المستخدمين</b>\n"
        f" 3⃣ أرسل معرف {ch_or_gr} أو رابطها العام\n"
        f"\n\n"
        f"<i>~ اقرأ الخطوات جيداً </i>",
        kb.back_keyboard())

@bot.message_handler(func=lambda m: True, content_types=['text', 'photo', 'video', 'document', 'sticker'])
def msg_router(msg: Message):
    tg_id = msg.from_user.id
    state = get_state(tg_id)
    s = state.get("state"); d = state.get("data", {})

    # استيراد قاعدة البيانات (يجب معالجته هنا لأن handler المنفصل يأتي متأخراً)
    if s == "db_import_input":
        if msg.content_type == "document":
            clear_state(tg_id)
            try:
                file_info = bot.get_file(msg.document.file_id)
                downloaded = bot.download_file(file_info.file_path)
                json_str = downloaded.decode("utf-8")
                ok, result_msg = db.import_db_json(json_str)
                if ok:
                    send(msg.chat.id, f"✅ <b>تم الاستيراد بنجاح!</b>\n{result_msg}")
                else:
                    send(msg.chat.id, f"❌ <b>فشل الاستيراد:</b>\n{result_msg}")
            except Exception as e:
                send(msg.chat.id, f"❌ خطأ: {e}")
        elif msg.text and msg.text.strip().lower() == "cancel":
            clear_state(tg_id)
            send(msg.chat.id, "✅ تم الإلغاء")
        else:
            send(msg.chat.id, "⚠️ أرسل ملف JSON فقط، أو أرسل cancel للإلغاء")
        return

    # المستخدم: إدخال كود دعوة
    if s == "waiting_invite_code":
        code = msg.text.strip().upper()
        ok, pts, err = db.claim_invite_code(tg_id, code)
        if ok:
            send(msg.chat.id,
                f" <b>تم تفعيل الكود!</b>\n\n حصلت على <b>{pts}</b> نقطة!",
                kb.back_keyboard())
        else:
            send(msg.chat.id, f" {err}", kb.back_keyboard())
        clear_state(tg_id); return

    #  إثبات دفع فودافون كاش للاشتراك 
    if s == "sub_vodafone_proof":
        plan_id = d.get("plan_id")
        plan = db.get_subscription_plan(plan_id) if plan_id else None
        proof_text = msg.text or ""
        if msg.photo:
            proof_text = f"[صورة] {msg.photo[-1].file_id}"
        if not plan:
            send(tg_id, " الخطة غير موجودة", kb.back_keyboard()); clear_state(tg_id); return
        rid = db.create_subscription_request(tg_id, plan_id, "vodafone", proof=proof_text)
        send(tg_id,
            f" <b>تم إرسال طلب الاشتراك!</b>\n\n"
            f"{plan['emoji']} <b>{plan['name']}</b>\n"
            f" رقم الطلب: <b>#{rid}</b>\n\n"
            f"<i>سيتم مراجعة الطلب وتفعيل اشتراكك قريباً.</i>",
            kb.back_keyboard())
        for adm in config.ADMIN_IDS:
            try:
                bot.send_message(adm,
                    f" <b>طلب اشتراك جديد #{rid}</b>\n\n"
                    f" <code>{tg_id}</code>  {msg.from_user.full_name}\n"
                    f"{plan['emoji']} الخطة: <b>{plan['name']}</b>\n"
                    f" طريقة: فودافون كاش\n"
                    f" الإثبات: {proof_text[:100]}")
            except Exception: pass
        clear_state(tg_id); return

    #  إثبات دفع USDT للاشتراك 
    if s == "sub_usdt_proof":
        plan_id = d.get("plan_id")
        plan = db.get_subscription_plan(plan_id) if plan_id else None
        proof_text = msg.text or ""
        if msg.photo:
            proof_text = f"[صورة] {msg.photo[-1].file_id}"
        if not plan:
            send(tg_id, " الخطة غير موجودة", kb.back_keyboard()); clear_state(tg_id); return
        rid = db.create_subscription_request(tg_id, plan_id, "usdt", proof=proof_text)
        send(tg_id,
            f" <b>تم إرسال طلب الاشتراك!</b>\n\n"
            f"{plan['emoji']} <b>{plan['name']}</b>\n"
            f" رقم الطلب: <b>#{rid}</b>\n\n"
            f"<i>سيتم مراجعة الطلب وتفعيل اشتراكك قريباً.</i>",
            kb.back_keyboard())
        for adm in config.ADMIN_IDS:
            try:
                bot.send_message(adm,
                    f" <b>طلب اشتراك جديد #{rid}</b>\n\n"
                    f" <code>{tg_id}</code>  {msg.from_user.full_name}\n"
                    f"{plan['emoji']} الخطة: <b>{plan['name']}</b>\n"
                    f" طريقة: USDT\n"
                    f" الإثبات: {proof_text[:100]}")
            except Exception: pass
        clear_state(tg_id); return

    if not is_admin(tg_id): return

    #  إضافة قسم جديد 
    if s == "adm_add_app":
        try:
            parts = msg.text.strip().split("|")
            name = parts[0].strip()
            emoji = parts[1].strip() if len(parts) > 1 else ""
            db.add_app(name, emoji)
            send(msg.chat.id, f" تم إضافة القسم: {emoji} {name}",
                 kb.admin_apps_keyboard(db.get_apps(only_active=False)))
        except Exception:
            send(msg.chat.id, " الشكل غير صحيح! استخدم: <code>الاسم|الإيموجي</code>")
        clear_state(tg_id); return

    #  إضافة خدمة (مبسّطة - يجيب البيانات من API) 
    if s == "adm_add_svc":
        try:
            parts = [p.strip() for p in msg.text.strip().split("|")]
            if len(parts) < 2:
                raise ValueError("لازم على الأقل: SERVICE_ID|نقاط")

            api_id = parts[0]
            ppu = int(parts[1])
            custom_emoji = parts[2] if len(parts) > 2 and parts[2] else ""
            custom_name = parts[3] if len(parts) > 3 and parts[3] else None

            # جلب بيانات الخدمة من SMMParty
            send(msg.chat.id, "⏳ جاري جلب بيانات الخدمة من الموقع...")
            info = smm.get_service_info(api_id)
            if not info:
                raise ValueError(f"لم يتم العثور على خدمة بالـ ID: {api_id}")

            name = custom_name or info.get("name", f"خدمة {api_id}")
            try:    mn = int(info.get("min", 100))
            except: mn = 100
            try:    mx = int(info.get("max", 100000))
            except: mx = 100000
            try:    rate = float(info.get("rate", 0.5))
            except: rate = 0.5

            app_id = d["app_id"]
            db.add_service(app_id, name, custom_emoji, api_id, ppu, mn, mx, rate)

            send(msg.chat.id,
                f" <b>تم إضافة الخدمة بنجاح!</b>\n\n"
                f"\n"
                f"{custom_emoji} <b>{name}</b>\n"
                f" API: <code>{api_id}</code>\n"
                f" السعر: <b>{ppu}</b> نقطة/وحدة\n"
                f" الحدود: {mn:,} - {mx:,}\n"
                f" سعر الموقع: {rate}$/1000\n"
                f"\n"
                f"<i> تم جلب الاسم والحدود تلقائياً</i>",
                kb.admin_app_view_keyboard(app_id, db.get_app_services(app_id, only_active=False)))
        except Exception as e:
            send(msg.chat.id,
                f" خطأ: {e}\n\n"
                f"<b>الشكل الصحيح:</b>\n"
                f"<code>SERVICE_ID|نقاط_الوحدة</code>\n"
                f"أو:\n"
                f"<code>SERVICE_ID|نقاط_الوحدة|الإيموجي|اسم_مخصص</code>")
        clear_state(tg_id); return

    #  إضافة جائزة لعجلة الحظ 
    if s == "adm_wheel_add":
        try:
            parts = [p.strip() for p in msg.text.strip().split("|")]
            if len(parts) < 2:
                raise ValueError("لازم: النقاط|الوزن")
            points = int(parts[0])
            weight = float(parts[1])
            emoji = parts[2] if len(parts) > 2 and parts[2] else ""
            if points <= 0 or weight <= 0:
                raise ValueError("القيم لازم تكون أكبر من صفر")
            db.add_wheel_prize(points, weight, emoji)
            send(msg.chat.id,
                f" <b>تم إضافة الجائزة بنجاح!</b>\n\n"
                f"{emoji} <b>{points}</b> نقطة | وزن: {weight:g}",
                kb.back_keyboard("adm_wheel"))
        except Exception as e:
            send(msg.chat.id,
                f" خطأ: {e}\n\n<b>الشكل الصحيح:</b>\n"
                f"<code>النقاط|الوزن|الإيموجي</code>")
        clear_state(tg_id); return

    if s == "adm_add_mand_step1":
        ch_id = msg.text.strip()
        set_state(tg_id, "adm_add_mand_step2", channel_id=ch_id)
        send(msg.chat.id,
            f" المعرف: <code>{ch_id}</code>\n\n"
            f"<b>الخطوة 2/4:</b>\nأرسل اسم القناة (للعرض):",
            kb.back_keyboard("adm_mandatory"))
        return

    if s == "adm_add_mand_step2":
        name = msg.text.strip()
        set_state(tg_id, "adm_add_mand_step3", channel_id=d["channel_id"], name=name)
        send(msg.chat.id,
            f" الاسم: <b>{name}</b>\n\n"
            f"<b>الخطوة 3/4:</b>\nأرسل رابط القناة (مثل: <code>https://t.me/channel</code>):",
            kb.back_keyboard("adm_mandatory"))
        return

    if s == "adm_add_mand_step3":
        url = msg.text.strip()
        set_state(tg_id, "adm_add_mand_step4",
                  channel_id=d["channel_id"], name=d["name"], url=url)
        send(msg.chat.id,
            f" الرابط مسجَّل\n\n"
            f"<b>الخطوة 4/4:</b>\n"
            f"أرسل عدد الأعضاء المطلوب اشتراكهم بهذه القناة\n"
            f"<i>(عند الوصول للعدد ستُحذف القناة من الاشتراك الإجباري تلقائياً)</i>\n\n"
            f" أرسل <code>0</code> = بدون حد",
            kb.back_keyboard("adm_mandatory"))
        return

    if s == "adm_add_mand_step4":
        try:
            target = int(msg.text.strip())
            ok = db.add_mandatory_channel(d["channel_id"], d["name"], d["url"], target)
            if ok:
                send(msg.chat.id,
                    f" <b>تمت الإضافة بنجاح!</b>\n\n"
                    f" {d['name']}\n"
                    f" الهدف: {'بدون حد' if target == 0 else f'{target:,} عضو'}\n\n"
                    f"<i>سيتم حذف القناة تلقائياً عند الوصول للهدف </i>",
                    kb.admin_main_keyboard())
            else:
                send(msg.chat.id, " القناة موجودة مسبقاً!", kb.admin_main_keyboard())
        except ValueError:
            send(msg.chat.id, " أرسل رقماً صحيحاً!"); return
        clear_state(tg_id); return

    #  إعدادات 
    if s == "adm_set_service_id":
        db.set_config("service_id", msg.text.strip())
        send(msg.chat.id, f" تم التحديث", kb.admin_service_keyboard())
        clear_state(tg_id); return

    if s == "adm_set_price":
        try:
            db.set_config("price_per_1000", str(float(msg.text.strip())))
            send(msg.chat.id, " تم التحديث", kb.admin_service_keyboard())
        except ValueError: send(msg.chat.id, " رقم غير صحيح")
        clear_state(tg_id); return

    if s == "adm_set_min_qty":
        try:
            v = int(msg.text.strip())
            if v < 1: raise ValueError()
            db.set_config("service_min", str(v))
            send(msg.chat.id, f" تم تغيير الحد الأدنى إلى <b>{v}</b> عضو", kb.admin_service_keyboard())
        except ValueError: send(msg.chat.id, " أرسل رقماً صحيحاً أكبر من صفر!")
        clear_state(tg_id); return

    if s == "adm_set_stars_rate":
        try:
            v = int(msg.text.strip())
            if v < 1: raise ValueError()
            db.set_config("stars_per_point", str(v))
            send(msg.chat.id, f" تم: <b>1 نجمة = {v} نقطة</b>", kb.admin_charge_settings_keyboard())
        except ValueError: send(msg.chat.id, " أرسل رقماً صحيحاً!")
        clear_state(tg_id); return

    if s == "adm_set_stars_post":
        val = msg.text.strip()
        if val == "0":
            db.set_config("stars_post_link", "")
            send(msg.chat.id, "✅ تم إلغاء ربط منشور النجوم.", kb.admin_charge_settings_keyboard())
        elif val.startswith("https://t.me/"):
            db.set_config("stars_post_link", val)
            send(msg.chat.id,
                f"✅ <b>تم حفظ رابط المنشور!</b>\n\n"
                f"⭐ الرابط: <code>{val}</code>\n\n"
                f"كل مشتري بالنجوم سيصله forward من هذا المنشور تلقائياً.",
                kb.admin_charge_settings_keyboard())
        else:
            send(msg.chat.id,
                "❌ الرابط غير صحيح! لازم يبدأ بـ <code>https://t.me/</code>",
                kb.back_keyboard("adm_charge_settings"))
            return
        clear_state(tg_id); return

    if s == "adm_set_cash_rate":
        try:
            v = int(msg.text.strip())
            if v < 1: raise ValueError()
            db.set_config("cash_rate", str(v))
            send(msg.chat.id, f" تم: <b>1$ = {v} نقطة</b>", kb.admin_charge_settings_keyboard())
        except ValueError: send(msg.chat.id, " أرسل رقماً صحيحاً!")
        clear_state(tg_id); return

    if s == "adm_set_usdt_rate":
        try:
            parts = [p.strip() for p in msg.text.strip().split("|")]
            v = int(parts[0])
            wallet = parts[1] if len(parts) > 1 else db.get_config("usdt_wallet", "")
            if v < 1: raise ValueError()
            db.set_config("usdt_rate", str(v))
            db.set_config("usdt_wallet", wallet)
            send(msg.chat.id,
                f" تم:\n<b>1 USDT = {v} نقطة</b>\n المحفظة: <code>{wallet}</code>",
                kb.admin_charge_settings_keyboard())
        except ValueError: send(msg.chat.id, " الشكل الصحيح: <code>النقاط|عنوان_المحفظة</code>")
        clear_state(tg_id); return

    if s in ("adm_set_daily_pts", "adm_set_weekly_pts", "adm_set_ref_pts", "adm_set_member_price"):
        key_map = {
            "adm_set_daily_pts":  "daily_gift_points",
            "adm_set_weekly_pts": "weekly_gift_points",
            "adm_set_ref_pts":    "referral_points",
            "adm_set_member_price": "points_per_member",
        }
        try:
            v = int(msg.text.strip())
            db.set_config(key_map[s], str(v))
            send(msg.chat.id, f" تم: <b>{v}</b>", kb.admin_points_settings_keyboard())
        except ValueError: send(msg.chat.id, " أرسل رقماً!")
        clear_state(tg_id); return

    # ═══ إضافة قناة يدوياً للإذاعة ═══
    if s == "adm_bcast_manual_channel":
        clear_state(tg_id)
        raw = msg.text.strip() if msg.text else ""
        if not raw:
            send(msg.chat.id, "❌ لم ترسل شيئاً!"); return
        lines = [l.strip() for l in raw.splitlines() if l.strip()]
        bot_id = bot.get_me().id
        added_list = []
        fail_list = []

        conn_dc = db.get_conn()
        try:
            conn_dc.execute("""
                CREATE TABLE IF NOT EXISTS discovered_channels (
                    chat_id    TEXT PRIMARY KEY,
                    chat_title TEXT DEFAULT '',
                    chat_type  TEXT DEFAULT '',
                    added_at   TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn_dc.commit()
        except Exception: pass

        for line in lines:
            cid = line
            if cid.startswith("https://t.me/"):
                cid = "@" + cid.split("https://t.me/")[-1].split("/")[0]
            try:
                member = bot.get_chat_member(cid, bot_id)
                if member.status in ("administrator", "creator"):
                    try:
                        chat_info = bot.get_chat(cid)
                        title = chat_info.title or str(cid)
                        real_id = str(chat_info.id)
                        chat_type = chat_info.type or "channel"
                    except Exception:
                        title = str(cid); real_id = str(cid); chat_type = "channel"
                    conn_dc.execute(
                        "INSERT OR REPLACE INTO discovered_channels(chat_id, chat_title, chat_type) VALUES(?,?,?)",
                        (real_id, title, chat_type)
                    )
                    conn_dc.commit()
                    added_list.append(f"✅ {title} (<code>{real_id}</code>)")
                else:
                    fail_list.append(f"❌ {cid} — البوت مش أدمن فيها")
            except Exception as ex:
                fail_list.append(f"❌ {cid} — خطأ: {str(ex)[:40]}")

        conn_dc.close()
        total_now = len(_bcast_get_all_channels_full())
        result = f"➕ <b>نتيجة الإضافة اليدوية</b>\n{'─'*26}\n"
        if added_list:
            result += "\n".join(added_list) + "\n"
        if fail_list:
            result += "\n".join(fail_list) + "\n"
        result += f"\n📢 إجمالي القنوات الآن: <b>{total_now}</b>"
        send(msg.chat.id, result,
             InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع للإذاعة", callback_data="adm_broadcast")]]))
        return

    # ═══ إذاعة بسيطة (نص/صورة/فيديو) ═══
    if s == "adm_bcast_msg_simple":
        target = d.get("target", "all")
        target_label = {"all": "👥+📢 الكل", "users": "👥 مستخدمون", "channels": "📢 قنوات"}.get(target, target)
        clear_state(tg_id)
        prog = send(msg.chat.id,
            f"📡 <b>جاري الإذاعة...</b>\n\n"
            f"🎯 الهدف: {target_label}\n"
            f"<code>{'░'*12} 0%</code>\n"
            f"⏳ يرجى الانتظار...")
        threading.Thread(
            target=_run_broadcast,
            kwargs=dict(
                admin_id=tg_id, progress_msg_id=prog.message_id, progress_chat_id=msg.chat.id,
                target=target, msg_chat_id=msg.chat.id, msg_id=msg.message_id,
                brd_msg_obj=msg
            ),
            daemon=True
        ).start()
        return

    # ═══ إذاعة مع زر — الخطوة 1: نص الزر ═══
    if s == "adm_bcast_btn1_text":
        btn_text = msg.text.strip() if msg.text else ""
        if not btn_text:
            send(msg.chat.id, "❌ أرسل نص الزر!"); return
        target = d.get("target", "all")
        set_state(tg_id, "adm_bcast_btn2_url", target=target, btn_text=btn_text)
        send(msg.chat.id,
            f"✅ نص الزر: <b>{btn_text}</b>\n\n"
            f"<b>الخطوة 2/3:</b> أرسل <b>رابط الزر</b>:\n"
            f"مثال: <code>https://t.me/mychannel</code>",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast")]])); return

    # ═══ إذاعة مع زر — الخطوة 2: رابط الزر ═══
    if s == "adm_bcast_btn2_url":
        btn_url = msg.text.strip() if msg.text else ""
        if not btn_url.startswith("http"):
            send(msg.chat.id, "❌ الرابط يجب أن يبدأ بـ <code>https://</code>"); return
        set_state(tg_id, "adm_bcast_btn3_msg",
                  target=d.get("target", "all"),
                  btn_text=d.get("btn_text"), btn_url=btn_url)
        send(msg.chat.id,
            f"✅ الرابط: <code>{btn_url}</code>\n\n"
            f"<b>الخطوة 3/3:</b> أرسل <b>نص رسالة الإذاعة</b>:",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast")]])); return

    # ═══ إذاعة مع زر — الخطوة 3: نص الرسالة ═══
    if s == "adm_bcast_btn3_msg":
        brd_text = msg.text.strip() if msg.text else ""
        if not brd_text:
            send(msg.chat.id, "❌ أرسل نص الرسالة!"); return
        btn_text = d.get("btn_text"); btn_url = d.get("btn_url"); target = d.get("target", "all")
        target_label = {"all": "👥+📢 الكل", "users": "👥 مستخدمون", "channels": "📢 قنوات"}.get(target, target)
        clear_state(tg_id)
        prog = send(msg.chat.id,
            f"📡 <b>جاري الإذاعة...</b>\n\n"
            f"🎯 الهدف: {target_label}\n"
            f"🔗 الزر: <b>{btn_text}</b>\n"
            f"<code>{'░'*12} 0%</code>\n"
            f"⏳ يرجى الانتظار...")
        threading.Thread(
            target=_run_broadcast,
            kwargs=dict(
                admin_id=tg_id, progress_msg_id=prog.message_id, progress_chat_id=msg.chat.id,
                target=target, msg_chat_id=msg.chat.id, msg_id=msg.message_id,
                btn_text=btn_text, btn_url=btn_url, brd_text=brd_text
            ),
            daemon=True
        ).start()
        return

    # ═══ دعم الأسماء القديمة للتوافق ═══
    if s == "adm_broadcast":
        target = d.get("target", "all")
        clear_state(tg_id)
        prog = send(msg.chat.id,
            f"📡 <b>جاري الإذاعة...</b>\n\n"
            f"<code>{'░'*12} 0%</code>\n⏳ يرجى الانتظار...")
        threading.Thread(
            target=_run_broadcast,
            kwargs=dict(
                admin_id=tg_id, progress_msg_id=prog.message_id, progress_chat_id=msg.chat.id,
                target=target, msg_chat_id=msg.chat.id, msg_id=msg.message_id,
                brd_msg_obj=msg
            ),
            daemon=True
        ).start()
        return

    if s == "adm_broadcast_btn_text":
        btn_text = msg.text.strip() if msg.text else ""
        if not btn_text:
            send(msg.chat.id, "❌ أرسل نص الزر!"); return
        set_state(tg_id, "adm_bcast_btn2_url", target="all", btn_text=btn_text)
        send(msg.chat.id,
            f"✅ نص الزر: <b>{btn_text}</b>\n\n<b>الخطوة 2/3:</b> أرسل رابط الزر:",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast")]])); return

    if s == "adm_broadcast_btn_url":
        btn_url = msg.text.strip() if msg.text else ""
        if not btn_url.startswith("http"):
            send(msg.chat.id, "❌ الرابط يجب أن يبدأ بـ https://"); return
        set_state(tg_id, "adm_bcast_btn3_msg", target="all",
                  btn_text=d.get("btn_text"), btn_url=btn_url)
        send(msg.chat.id,
            f"✅ الرابط: <code>{btn_url}</code>\n\n<b>الخطوة 3/3:</b> أرسل نص الرسالة:",
            InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="adm_broadcast")]])); return

    if s == "adm_broadcast_btn_msg":
        brd_text = msg.text.strip() if msg.text else ""
        if not brd_text:
            send(msg.chat.id, "❌ أرسل نص الرسالة!"); return
        btn_text = d.get("btn_text"); btn_url = d.get("btn_url")
        clear_state(tg_id)
        prog = send(msg.chat.id, f"📡 <b>جاري الإذاعة...</b>\n\n<code>{'░'*12} 0%</code>")
        threading.Thread(
            target=_run_broadcast,
            kwargs=dict(
                admin_id=tg_id, progress_msg_id=prog.message_id, progress_chat_id=msg.chat.id,
                target="all", msg_chat_id=msg.chat.id, msg_id=msg.message_id,
                btn_text=btn_text, btn_url=btn_url, brd_text=brd_text
            ),
            daemon=True
        ).start()
        return

    if s == "adm_add_admin_id":
        if msg.from_user.id not in config.ADMIN_IDS:
            send(msg.chat.id, " ليس لديك صلاحية"); clear_state(tg_id); return
        try:
            parts = [p.strip() for p in (msg.text or "").strip().split("|")]
            new_admin_id = int(parts[0])
            note = parts[1] if len(parts) > 1 else ""
            # لا تضف أدمن موجود في config
            if new_admin_id in config.ADMIN_IDS:
                send(msg.chat.id, " هذا المستخدم أدمن أصلي بالفعل!"); clear_state(tg_id); return
            ok = db.add_dynamic_admin(new_admin_id, str(tg_id) + (" | " + note if note else ""))
            if ok:
                u = db.get_user(new_admin_id)
                name = (u["full_name"] or u["username"] or str(new_admin_id)) if u else str(new_admin_id)
                send(msg.chat.id,
                    f" <b>تم إضافة أدمن جديد!</b>\n\n"
                    f" الاسم: <b>{name}</b>\n"
                    f" ID: <code>{new_admin_id}</code>\n"
                    f" ملاحظة: {note or ''}",
                    kb.back_keyboard("adm_manage_admins"))
                try:
                    bot.send_message(new_admin_id,
                        f" <b>تهانينا! تمت ترقيتك لأدمن في {config.BOT_NAME}!</b>\n\n"
                        f"استخدم الأمر /admin للوصول للوحة الأدمن.",
                        parse_mode="HTML")
                except Exception: pass
            else:
                send(msg.chat.id, " هذا المستخدم مضاف أدمن بالفعل!",
                     kb.back_keyboard("adm_manage_admins"))
        except (ValueError, IndexError):
            send(msg.chat.id, " أرسل ID صحيح أو بالشكل: <code>ID|ملاحظة</code>")
        clear_state(tg_id); return

    if s == "adm_topup_id":
        try:
            target = int(msg.text.strip())
            if not db.get_user(target):
                send(msg.chat.id, " المستخدم غير موجود!"); clear_state(tg_id); return
            set_state(tg_id, "adm_topup_amount", target_id=target)
            send(msg.chat.id, f" أرسل عدد النقاط لـ <code>{target}</code>:")
        except ValueError:
            send(msg.chat.id, " ID غير صحيح"); clear_state(tg_id)
        return

    if s == "adm_topup_amount":
        try:
            amt = int(msg.text.strip())
            target = d.get("target_id")
            db.add_points(target, amt)
            send(msg.chat.id, f" تم شحن <b>{amt}</b> نقطة", kb.admin_main_keyboard())
            try: bot.send_message(target, f" <b>تم شحن نقاطك!</b>\n\n+ <b>{amt}</b> نقطة")
            except Exception: pass
        except ValueError: send(msg.chat.id, " رقم غير صحيح")
        clear_state(tg_id); return

    if s == "adm_set_updates_ch":
        db.set_config("updates_channel", msg.text.strip())
        send(msg.chat.id, " تم", kb.admin_main_keyboard()); clear_state(tg_id); return

    if s == "adm_set_bot_channel":
        val = msg.text.strip()
        db.set_config("bot_channel", "" if val == "-" else val)
        send(msg.chat.id, " تم ضبط قناة البوت", kb.admin_main_keyboard()); clear_state(tg_id); return

    if s == "adm_set_support":
        db.set_config("support_username", msg.text.strip())
        send(msg.chat.id, " تم", kb.admin_main_keyboard()); clear_state(tg_id); return

    #  إضافة خطة اشتراك 
    if s == "adm_sub_add":
        try:
            parts = [p.strip() for p in msg.text.strip().split("|")]
            if len(parts) < 6:
                raise ValueError("الشكل: الاسم|إيموجي|الأيام|نجوم|فودافون|USDT|وصف")
            name         = parts[0]
            emoji        = parts[1] if parts[1] else ""
            duration     = int(parts[2])
            price_stars  = int(parts[3])
            price_vodafone = int(parts[4])
            price_usdt   = float(parts[5])
            description  = parts[6] if len(parts) > 6 else ""
            pid = db.add_subscription_plan(name, emoji, duration, price_stars, price_vodafone, price_usdt, description)
            send(msg.chat.id,
                f" <b>تم إضافة خطة الاشتراك!</b>\n\n"
                f"{emoji} <b>{name}</b>\n"
                f" {duration} يوم\n"
                f" نجوم: {price_stars} |  فودافون: {price_vodafone} ج |  USDT: {price_usdt}$",
                kb.back_keyboard("adm_subscriptions"))
        except Exception as e:
            send(msg.chat.id,
                f" خطأ: {e}\n\n<b>الشكل الصحيح:</b>\n"
                f"<code>الاسم|إيموجي|الأيام|نجوم|فودافون|USDT|وصف</code>")
        clear_state(tg_id); return

    #  تعديل اسم زر 
    if s == "adm_btn_edit":
        btn_key = d.get("btn_key")
        text_input = msg.text.strip() if msg.text else ""
        if "|" in text_input:
            parts = text_input.split("|", 1)
            emoji = parts[0].strip()
            text  = parts[1].strip()
        else:
            emoji = None
            text  = text_input
        lbl_full = (emoji + "|" + text) if emoji else text
        db.set_button_label(btn_key, lbl_full)
        send(msg.chat.id,
            f" <b>تم تحديث الزر!</b>\n\n"
            f"<code>{btn_key}</code> → {emoji or ''} {text}",
            kb.back_keyboard("adm_button_labels"))
        clear_state(tg_id); return

    #  ضبط إيموجي مميز لزر 
    if s == "adm_btn_emo_input":
        target_cb = d.get("target_cb", "")

        # حالة: المستخدم بعت ستيكر أو إيموجي مميز مباشرة
        emoji_id = None
        if msg.sticker and msg.sticker.custom_emoji_id:
            emoji_id = msg.sticker.custom_emoji_id
        elif msg.text:
            raw = msg.text.strip()
            if raw.lower() in ("cancel", "إلغاء"):
                send(msg.chat.id, "تم الإلغاء"); clear_state(tg_id); return
            if raw.isdigit():
                emoji_id = raw
            else:
                send(msg.chat.id,
                     "⚠️ أرسل <b>الإيموجي المميز مباشرة</b> (من لوحة الإيموجي) أو أرسل الـ ID كأرقام فقط.\n"
                     "أرسل <code>cancel</code> للإلغاء.")
                return
        else:
            send(msg.chat.id, "⚠️ أرسل الإيموجي أو الـ ID.\nأرسل <code>cancel</code> للإلغاء.")
            return

        db.set_btn_emoji(target_cb, emoji_id)
        _invalidate_btn_emoji_cache()
        label = _label_for_cb(target_cb)
        send(msg.chat.id,
             f"✅ تم ضبط الإيموجي للزر <b>{label}</b>\n"
             f"الـ ID: <code>{emoji_id}</code>",
             kb.back("adm_btn_emojis"))
        clear_state(tg_id); return

    #  إعداد رقم فودافون كاش 
    if s == "adm_set_vodafone_number":
        db.set_config("vodafone_number", msg.text.strip())
        send(msg.chat.id, " تم ضبط رقم فودافون كاش", kb.admin_main_keyboard())
        clear_state(tg_id); return

    if s == "adm_add_ptch_data":
        try:
            parts = msg.text.strip().split("|")
            ok = db.add_points_channel(parts[0].strip(), parts[1].strip(),
                                        parts[2].strip(), int(parts[3].strip()))
            send(msg.chat.id, " تمت الإضافة!" if ok else " موجودة مسبقاً",
                 kb.admin_main_keyboard())
        except Exception: send(msg.chat.id, " الشكل غير صحيح")
        clear_state(tg_id); return

    if s == "adm_search_user":
        try:
            target = int(msg.text.strip())
            user = db.get_user(target)
            if not user:
                send(msg.chat.id, " غير موجود!"); clear_state(tg_id); return
            ref_c = db.get_referral_count(target)
            send(msg.chat.id,
                f" <b>المستخدم</b>\n\n"
                f" <code>{target}</code>\n"
                f" {user['full_name']}\n"
                f" {user['points']:,} نقطة |  {ref_c} إحالة\n"
                f" محظور: {'نعم' if user['is_banned'] else 'لا'}",
                kb.admin_user_keyboard(target, bool(user["is_banned"])))
        except ValueError: send(msg.chat.id, " ID غير صحيح")
        clear_state(tg_id); return

    if s in ("adm_add_points", "adm_sub_points"):
        try:
            amt = int(msg.text.strip()); target = d.get("target_id")
            if s == "adm_add_points":
                db.add_points(target, amt)
                send(msg.chat.id, f" +{amt}", kb.admin_main_keyboard())
            else:
                if db.deduct_points(target, amt):
                    send(msg.chat.id, f" -{amt}", kb.admin_main_keyboard())
                else: send(msg.chat.id, " نقاط غير كافية", kb.admin_main_keyboard())
        except ValueError: send(msg.chat.id, " رقم غير صحيح")
        clear_state(tg_id); return

    if s == "adm_create_invite":
        try:
            parts = msg.text.strip().split("|")
            code = parts[0].strip().upper(); pts = int(parts[1].strip()); mx = int(parts[2].strip())
            ok = db.create_invite_link(code, pts, mx)
            if ok:
                bot_username = config.BOT_USERNAME.lstrip("@")
                url = f"https://t.me/{bot_username}?start=invite_{code}"
                send(msg.chat.id,
                    f" <b>تم الإنشاء!</b>\n\n"
                    f" <code>{code}</code>\n"
                    f" {pts} نقطة\n"
                    f" {'∞' if mx == 0 else mx}\n\n"
                    f" <code>{url}</code>",
                    kb.back_keyboard("adm_invite_links"))
            else:
                send(msg.chat.id, " الكود موجود!", kb.back_keyboard("adm_invite_links"))
        except Exception: send(msg.chat.id, " الشكل غير صحيح")
        clear_state(tg_id); return

    #  إضافة تمويل مكتمل 
    if s == "adm_add_funding":
        try:
            parts = [p.strip() for p in msg.text.strip().split("|")]
            if len(parts) < 3:
                raise ValueError("لازم على الأقل: العنوان|الإيموجي|عدد_الأعضاء")
            title   = parts[0]
            emoji_f = parts[1] if len(parts) > 1 else ""
            members = int(parts[2]) if len(parts) > 2 else 0
            desc    = parts[3] if len(parts) > 3 else ""
            ch_url  = parts[4] if len(parts) > 4 else ""
            fid = db.add_completed_funding(title, desc, emoji_f, members, ch_url)
            send(msg.chat.id,
                f" <b>تم إضافة التمويل المكتمل!</b>\n\n"
                f"{emoji_f} <b>{title}</b>\n"
                f" {members:,} عضو\n"
                f"{'<i>' + desc + '</i>' if desc else ''}\n"
                f"{' ' + ch_url if ch_url else ''}",
                kb.back_keyboard("adm_fundings"))
        except Exception as e:
            send(msg.chat.id,
                f" خطأ: {e}\n\n"
                f"<b>الشكل الصحيح:</b>\n"
                f"<code>العنوان|الإيموجي|عدد_الأعضاء|وصف|رابط</code>")
        clear_state(tg_id); return

    #  قناة التمويلات 
    if s == "adm_set_orders_ch":
        val = msg.text.strip()
        db.set_config("orders_channel", val)
        # اختبر القناة فوراً
        try:
            bot.send_message(val, " <b>تم ربط قناة التمويلات بنجاح!</b>", parse_mode="HTML")
            send(msg.chat.id, f" تم ضبط قناة التمويلات\n تم إرسال رسالة اختبار للقناة", kb.admin_main_keyboard())
        except Exception as e:
            send(msg.chat.id,
                f" تم الحفظ لكن  فشل إرسال رسالة الاختبار!\n\n"
                f"تأكد أن البوت أدمن في القناة:\n<code>{e}</code>",
                kb.admin_main_keyboard())
        clear_state(tg_id); return

    #  إنشاء رابط هدية 
    if s == "adm_create_gift_link":
        try:
            parts = [p.strip() for p in msg.text.strip().split("|")]
            points  = int(parts[0])
            max_use = int(parts[1]) if len(parts) > 1 else -1
            note    = parts[2] if len(parts) > 2 else ""
            code    = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
            db.create_gift_link(code, points, max_use, note)
            bu   = config.BOT_USERNAME.lstrip("@")
            link = f"https://t.me/{bu}?start=gift_{code}"
            gift_btn = InlineKeyboardMarkup()
            gift_btn.row(InlineKeyboardButton("🎁 رابط الهدية — اضغط للفتح 🎉", url=link))
            send(msg.chat.id,
                f"✅ <b>تم إنشاء رابط الهدية!</b>\n\n"
                f"⭐️ النقاط: <b>{points:,}</b>\n"
                f"🔢 الاستخدامات: {'غير محدود ♾' if max_use == -1 else max_use}\n"
                f"📝 ملاحظة: {note or 'لا يوجد'}\n\n"
                f"🔗 <b>الرابط:</b>\n<code>{link}</code>",
                gift_btn)
        except Exception as e:
            send(msg.chat.id,
                f" خطأ: {e}\n\n<b>الشكل الصحيح:</b>\n<code>النقاط|عدد_الاستخدامات|ملاحظة</code>")
        clear_state(tg_id); return

    #  إرسال هدية للقناة 
    if s == "adm_send_gift_to_channel":
        gid     = d.get("gid")
        channel = (msg.text or "").strip()
        conn    = db.get_conn()
        gl      = conn.execute("SELECT * FROM gift_links WHERE id=?", (gid,)).fetchone()
        conn.close()
        if not gl:
            send(msg.chat.id, " الرابط غير موجود!", kb.back_keyboard("adm_gift_links"))
            clear_state(tg_id); return
        bu      = config.BOT_USERNAME.lstrip("@")
        link_tg = f"https://t.me/{bu}?start=gift_{gl['code']}"
        note    = gl.get("note") or "هدية مجانية"
        m_gift  = InlineKeyboardMarkup()
        m_gift.row(InlineKeyboardButton(" استلم هديتك الآن! ", url=link_tg))
        try:
            bot.send_message(channel,
                f" <b>{note}</b>\n\n"
                f"\n"
                f"  <b>{gl['points']:,}</b> نقطة مجاناً!\n"
                f"  الكمية محدودة!\n"
                f"\n\n"
                f" اضغط واستلم هديتك الآن!",
                reply_markup=m_gift, parse_mode="HTML")
            send(msg.chat.id, " <b>تم إرسال الهدية للقناة بنجاح!</b>",
                 kb.back_keyboard("adm_gift_links"))
        except Exception as e:
            send(msg.chat.id,
                f" <b>فشل الإرسال!</b>\nتأكد إن البوت أدمن في القناة.\n<code>{e}</code>",
                kb.back_keyboard("adm_gift_links"))
        clear_state(tg_id); return

    #  إضافة منتج في المتجر 
    if s == "adm_shop_add":
        try:
            parts = [p.strip() for p in msg.text.strip().split("|")]
            name = parts[0]; emoji_s = parts[1] if len(parts) > 1 else ""
            desc = parts[2] if len(parts) > 2 else ""
            price = int(parts[3]) if len(parts) > 3 else 100
            stock = int(parts[4]) if len(parts) > 4 else -1
            iid = db.add_shop_item(name, desc, emoji_s, price, stock)
            send(msg.chat.id,
                f" <b>تم إضافة المنتج!</b>\n\n"
                f"{emoji_s} <b>{name}</b>\n"
                f" السعر: <b>{price:,}</b> نقطة\n"
                f" المخزون: {'∞' if stock == -1 else stock}",
                kb.back_keyboard("adm_shop"))
        except Exception as e:
            send(msg.chat.id, f" خطأ: {e}\n\nالشكل: <code>الاسم||الوصف|السعر|المخزون</code>")
        clear_state(tg_id); return

    #  إضافة وكيل 
    if s == "adm_add_reseller":
        try:
            parts = [p.strip() for p in msg.text.strip().split("|")]
            uid = int(parts[0]); code = parts[1]; disc = int(parts[2])
            ok = db.add_reseller(uid, full_name=code, discount=disc)
            if ok:
                send(msg.chat.id,
                    f" <b>تم إضافة الوكيل!</b>\n\n"
                    f" ID: <code>{uid}</code>\n"
                    f" كود: <code>{code}</code>\n"
                    f" خصم: <b>{disc}%</b>",
                    kb.admin_main_keyboard())
            else:
                send(msg.chat.id, " الوكيل موجود مسبقاً!", kb.admin_main_keyboard())
        except Exception as e:
            send(msg.chat.id, f" خطأ: {e}\n\nالشكل: <code>ID|كود|الخصم</code>")
        clear_state(tg_id); return

    #  شحن بـ USDT (إرسال الإثبات) 
    if s == "charge_usdt_proof":
        proof = msg.text.strip() if msg.text else ""
        if msg.photo:
            proof = f"[صورة] {msg.photo[-1].file_id}"
        if not proof:
            send(msg.chat.id, " أرسل إثبات التحويل (صورة أو نص)"); return
        set_state(tg_id, "charge_usdt_amount", proof=proof)
        send(msg.chat.id, " أرسل كمية الـ USDT التي دفعتها:", kb.back_keyboard("charge_menu"))
        return

    if s == "charge_usdt_amount":
        try:
            amt = float(msg.text.strip())
            if amt <= 0: raise ValueError()
            usdt_rate = int(db.get_config("usdt_rate", "1"))
            pts = int(amt * usdt_rate)
            proof = d.get("proof", "")
            rid = db.create_charge_request(tg_id, "usdt", proof=proof, amount=pts)
            send(msg.chat.id,
                f" <b>تم إرسال طلب الشحن!</b>\n\n"
                f" المبلغ: <b>{amt} USDT</b>\n"
                f" النقاط المتوقعة: <b>{pts:,}</b>\n\n"
                f"<i>سيتم المراجعة وإضافة النقاط قريباً ⏳</i>",
                kb.back_keyboard())
            for adm in config.ADMIN_IDS:
                try:
                    bot.send_message(adm,
                        f" <b>طلب شحن USDT جديد #{rid}</b>\n\n"
                        f" <code>{tg_id}</code>  {msg.from_user.full_name}\n"
                        f" <b>{amt} USDT</b> ← <b>{pts:,}</b> نقطة\n"
                        f" الإثبات: {proof[:100]}",
                        reply_markup=InlineKeyboardMarkup().row(
                            kb._btn(f" قبول #{rid}", f"adm_charge_ok_{rid}", style="success"),
                            kb._btn(f" رفض", f"adm_charge_rej_{rid}", style="danger"),
                        ))
                except Exception: pass
        except ValueError:
            send(msg.chat.id, " أرسل رقماً صحيحاً!")
        clear_state(tg_id); return

    #  شحن بالكاش (إرسال الإثبات) 
    if s == "charge_cash_proof":
        proof = msg.text.strip() if msg.text else ""
        if msg.photo:
            proof = f"[صورة] {msg.photo[-1].file_id}"
        if not proof:
            send(msg.chat.id, " أرسل إثبات الدفع (نص أو صورة)"); return
        set_state(tg_id, "charge_cash_amount", proof=proof)
        send(msg.chat.id, " أرسل الكمية المطلوبة (عدد النقاط):", kb.back_keyboard("charge_menu"))
        return

    if s == "charge_cash_amount":
        try:
            amt = int(msg.text.strip())
            if amt <= 0: raise ValueError()
            proof = d.get("proof", "")
            rid = db.create_charge_request(tg_id, "cash", amt, proof=proof)
            send(msg.chat.id,
                f" <b>تم إرسال طلب الشحن!</b>\n\n"
                f" رقم الطلب: <b>#{rid}</b>\n"
                f" الكمية: <b>{amt:,}</b> نقطة\n\n"
                f"<i>سيتم المراجعة وإضافة النقاط قريباً ⏳</i>",
                kb.back_keyboard())
            # إشعار الأدمن
            for adm in config.ADMIN_IDS:
                try:
                    bot.send_message(adm,
                        f" <b>طلب شحن كاش جديد #{rid}</b>\n\n"
                        f" <code>{tg_id}</code>  {msg.from_user.full_name}\n"
                        f" <b>{amt:,}</b> نقطة\n"
                        f" الإثبات: {proof[:100]}",
                        reply_markup=InlineKeyboardMarkup().row(
                            kb._btn(f" قبول #{rid}", f"adm_charge_ok_{rid}", style="success"),
                            kb._btn(f" رفض", f"adm_charge_rej_{rid}", style="danger"),
                        ))
                except Exception: pass
        except ValueError:
            send(msg.chat.id, " أرسل رقماً صحيحاً!")
        clear_state(tg_id); return

    #  شحن عبر الوكيل (كود) 
    if s == "charge_reseller_code":
        code_input = msg.text.strip().upper()
        conn = sqlite3.connect(config.DB_PATH)
        conn.row_factory = sqlite3.Row
        res = conn.execute("SELECT * FROM resellers WHERE code=?", (code_input,)).fetchone()
        conn.close()
        if not res:
            send(msg.chat.id, " الكود غير صحيح!"); return
        set_state(tg_id, "charge_reseller_amount",
                  reseller_id=res["user_id"], discount=res["discount"])
        send(msg.chat.id,
            f" <b>كود الوكيل صحيح!</b>\n\n"
            f" خصم: <b>{res['discount']}%</b>\n\n"
            f" أرسل الكمية (عدد النقاط) للشحن:")
        return

    if s == "charge_reseller_amount":
        try:
            amt = int(msg.text.strip())
            if amt <= 0: raise ValueError()
            discount = d.get("discount", 0)
            final_pts = int(amt * (1 + discount / 100))
            rid = db.create_charge_request(tg_id, "reseller", final_pts,
                                            proof=f"وكيل خصم {discount}%")
            for adm in config.ADMIN_IDS:
                try:
                    bot.send_message(adm,
                        f" <b>طلب شحن وكيل #{rid}</b>\n\n"
                        f" <code>{tg_id}</code>\n"
                        f" {final_pts:,} نقطة (خصم {discount}%)",
                        reply_markup=InlineKeyboardMarkup().row(
                            kb._btn(f" قبول #{rid}", f"adm_charge_ok_{rid}", style="success"),
                            kb._btn(f" رفض", f"adm_charge_rej_{rid}", style="danger"),
                        ))
                except Exception: pass
            send(msg.chat.id,
                f" <b>تم إرسال طلب الشحن!</b>\n\n"
                f" <b>{final_pts:,}</b> نقطة (شامل خصم {discount}%)\n"
                f"<i>ينتظر مراجعة الأدمن ⏳</i>",
                kb.back_keyboard())
        except ValueError:
            send(msg.chat.id, " أرسل رقماً صحيحاً!")
        clear_state(tg_id); return

    #  تحويل نقاط: ID 
    if s == "transfer_waiting_id":
        try:
            target_id = int(msg.text.strip())
            if target_id == tg_id:
                send(msg.chat.id, " لا يمكنك التحويل لنفسك!"); return
            target_user = db.get_user(target_id)
            if not target_user:
                send(msg.chat.id, " المستخدم غير موجود!"); return
            set_state(tg_id, "transfer_waiting_amount", target_id=target_id,
                      target_name=target_user["full_name"] or str(target_id))
            send(msg.chat.id,
                f" التحويل إلى: <b>{target_user['full_name'] or target_id}</b>\n\n"
                f" أرسل عدد النقاط للتحويل:")
        except ValueError:
            send(msg.chat.id, " أرسل ID صحيح (أرقام فقط)")
        return

    if s == "transfer_waiting_amount":
        try:
            pts = int(msg.text.strip().replace(",", ""))
            if pts <= 0: raise ValueError()
            target_id = d.get("target_id")
            target_name = d.get("target_name", str(target_id))
            fee_pct = float(db.get_config("transfer_fee_pct", "0"))
            fee = int(pts * fee_pct / 100)
            total = pts + fee
            set_state(tg_id, "transfer_confirm",
                      target_id=target_id, target_name=target_name, pts=pts, fee=fee)
            user = db.get_user(tg_id)
            ok_bal = user["points"] >= total
            warn = "" if ok_bal else f"\n رصيدك <b>{user['points']:,}</b> غير كافٍ!"
            m = InlineKeyboardMarkup()
            if ok_bal:
                m.row(kb._btn(" تأكيد التحويل", "transfer_confirm", style="success"),
                      kb._btn("إلغاء", "back_main", style="danger"))
            else:
                m.row(kb._btn("رجوع", "back_main", style="danger"))
            send(msg.chat.id,
                f" <b>تأكيد التحويل</b>\n\n"
                f"\n"
                f" إلى: <b>{target_name}</b>\n"
                f" المبلغ: <b>{pts:,}</b> نقطة\n"
                f" الرسوم: <b>{fee:,}</b> نقطة\n"
                f" الإجمالي: <b>{total:,}</b> نقطة\n"
                f"{warn}", m)
        except ValueError:
            send(msg.chat.id, " أرسل رقماً صحيحاً!")
        return

    if s == "waiting_invite_code":
        code = msg.text.strip().upper()
        ok, pts, err = db.claim_invite_code(tg_id, code)
        if ok:
            send(msg.chat.id, f" <b>تم تفعيل الكود!</b>\n\n حصلت على <b>{pts}</b> نقطة!",
                 kb.back_keyboard())
        else:
            send(msg.chat.id, f" <b>{err}</b>", kb.back_keyboard())
        clear_state(tg_id); return

@bot.callback_query_handler(func=lambda c: c.data == "transfer_confirm")
def cb_transfer_confirm(call: CallbackQuery):
    state = get_state(call.from_user.id)
    if state.get("state") != "transfer_confirm":
        bot.answer_callback_query(call.id, " انتهت الجلسة"); return
    d = state.get("data", {})
    target_id = d.get("target_id"); pts = d.get("pts"); target_name = d.get("target_name")
    ok = db.transfer_points(call.from_user.id, target_id, pts)
    fee = 0
    err = "نقاطك غير كافية!"
    if ok:
        clear_state(call.from_user.id)
        user = db.get_user(call.from_user.id)
        edit(call,
            f" <b>تم التحويل بنجاح!</b>\n\n"
            f" أرسلت <b>{pts:,}</b> نقطة إلى <b>{target_name}</b>\n"
            f" الرسوم: <b>{fee:,}</b> نقطة\n"
            f" رصيدك المتبقي: <b>{user['points']:,}</b>",
            kb.back_keyboard())
        try:
            bot.send_message(target_id,
                f" <b>تلقيت تحويل نقاط!</b>\n\n"
                f" <b>+{pts:,}</b> نقطة من {call.from_user.full_name}\n"
                f" رصيدك: <b>{db.get_user(target_id)['points']:,}</b>")
        except Exception: pass
        orders_ch = db.get_config("orders_channel")
        if orders_ch:
            try:
                bot.send_message(orders_ch,
                    f" <b>تحويل نقاط</b>\n"
                    f"من <code>{call.from_user.id}</code> ← إلى <code>{target_id}</code>\n"
                    f" <b>{pts:,}</b> نقطة")
            except Exception: pass
    else:
        bot.answer_callback_query(call.id, f" {err}", show_alert=True)

# 
#   الاشتراك الإجباري  عرض الخطط
# 
@bot.callback_query_handler(func=lambda c: c.data == "subscription_plans")
def cb_subscription_plans(call: CallbackQuery):
    plans = db.get_subscription_plans(only_active=True)
    user_sub = db.get_active_subscription(call.from_user.id)
    sub_status = ""
    if user_sub:
        sub_status = (
            f"\n <b>اشتراكك الحالي:</b> {user_sub['plan_emoji']} {user_sub['plan_name']}\n"
            f" ينتهي: <b>{user_sub['end_date'][:10]}</b>\n"
        )
    if not plans:
        edit(call,
            f" <b>الاشتراك الإجباري</b>\n\n{sub_status}"
            f"<i>لا توجد خطط متاحة حالياً.</i>",
            kb.back_keyboard())
        return
    text = (
        f" <b>خطط الاشتراك الإجباري</b>\n\n"
        f"\n"
        f"{sub_status}"
        f"\n\n"
        f"اختر الخطة المناسبة لك:"
    )
    edit(call, text, kb.subscription_plans_keyboard(plans, user_sub))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sub_plan_"))
def cb_sub_plan(call: CallbackQuery):
    plan_id = int(call.data.split("_")[-1])
    plan = db.get_subscription_plan(plan_id)
    if not plan or not plan["is_active"]:
        bot.answer_callback_query(call.id, " الخطة غير متاحة", show_alert=True); return

    prices_txt = ""
    if plan["price_stars"] > 0:
        prices_txt += f" نجوم: <b>{plan['price_stars']}</b> نجمة\n"
    if plan["price_vodafone"] > 0:
        prices_txt += f" فودافون كاش: <b>{plan['price_vodafone']}</b> جنيه\n"
    if plan["price_usdt"] > 0:
        prices_txt += f" USDT: <b>{plan['price_usdt']}</b> دولار\n"

    edit(call,
        f"{plan['emoji']} <b>{plan['name']}</b>\n\n"
        f"\n"
        f" المدة: <b>{plan['duration_days']}</b> يوم\n"
        f" {plan['description'] or 'اشتراك إجباري مميز'}\n\n"
        f" <b>طرق الدفع:</b>\n{prices_txt}"
        f"\n\n"
        f"اختر طريقة الدفع:",
        kb.subscription_payment_keyboard(plan_id))

#  دفع بالنجوم 
@bot.callback_query_handler(func=lambda c: c.data.startswith("sub_pay_stars_"))
def cb_sub_pay_stars(call: CallbackQuery):
    plan_id = int(call.data.split("_")[-1])
    plan = db.get_subscription_plan(plan_id)
    if not plan or plan["price_stars"] <= 0:
        bot.answer_callback_query(call.id, " الدفع بالنجوم غير متاح لهذه الخطة", show_alert=True); return
    stars = plan["price_stars"]
    prices = [telebot.types.LabeledPrice(label=f"{plan['emoji']} {plan['name']}", amount=stars)]
    try:
        bot.send_invoice(
            call.message.chat.id,
            title=f"اشتراك {plan['name']}",
            description=f"{plan['emoji']} اشتراك {plan['name']}  {plan['duration_days']} يوم",
            invoice_payload=f"sub_stars_{call.from_user.id}_{plan_id}",
            provider_token="",
            currency="XTR",
            prices=prices,
        )
        bot.answer_callback_query(call.id)
    except Exception as e:
        bot.answer_callback_query(call.id, f" خطأ: {e}", show_alert=True)

#  دفع بفودافون كاش 
@bot.callback_query_handler(func=lambda c: c.data.startswith("sub_pay_vodafone_"))
def cb_sub_pay_vodafone(call: CallbackQuery):
    plan_id = int(call.data.split("_")[-1])
    plan = db.get_subscription_plan(plan_id)
    if not plan or plan["price_vodafone"] <= 0:
        bot.answer_callback_query(call.id, " دفع فودافون كاش غير متاح لهذه الخطة", show_alert=True); return
    vodafone_num = db.get_config("vodafone_number", "غير محدد")
    set_state(call.from_user.id, "sub_vodafone_proof", plan_id=plan_id)
    edit(call,
        f" <b>دفع بفودافون كاش</b>\n\n"
        f"\n"
        f"{plan['emoji']} الخطة: <b>{plan['name']}</b>\n"
        f" المبلغ: <b>{plan['price_vodafone']}</b> جنيه\n"
        f" رقم فودافون كاش: <code>{vodafone_num}</code>\n"
        f"\n\n"
        f" بعد الدفع أرسل صورة الإيصال أو رقم العملية:",
        kb.back_keyboard("subscription_plans"))

#  دفع بـ USDT 
@bot.callback_query_handler(func=lambda c: c.data.startswith("sub_pay_usdt_"))
def cb_sub_pay_usdt(call: CallbackQuery):
    plan_id = int(call.data.split("_")[-1])
    plan = db.get_subscription_plan(plan_id)
    if not plan or plan["price_usdt"] <= 0:
        bot.answer_callback_query(call.id, " دفع USDT غير متاح لهذه الخطة", show_alert=True); return
    wallet = db.get_config("usdt_wallet", "")
    wallet_line = f" عنوان المحفظة (TRC20):\n<code>{wallet}</code>" if wallet else " تواصل مع الدعم للمحفظة"
    set_state(call.from_user.id, "sub_usdt_proof", plan_id=plan_id)
    edit(call,
        f" <b>دفع بـ USDT</b>\n\n"
        f"\n"
        f"{plan['emoji']} الخطة: <b>{plan['name']}</b>\n"
        f" المبلغ: <b>{plan['price_usdt']}</b> USDT\n"
        f"{wallet_line}\n"
        f"\n\n"
        f" بعد التحويل أرسل صورة الإيصال أو هاش المعاملة:",
        kb.back_keyboard("subscription_plans"))

#  معالجة الدفع بالنجوم (successful_payment) 
# (يتم في successful_payment handler الموجود - نضيف منطق الاشتراك)

# 
#   لوحة الأدمن  إدارة الاشتراكات
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_subscriptions")
def cb_adm_subscriptions(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    plans = db.get_subscription_plans(only_active=False)
    pending = db.get_pending_subscription_requests()
    edit(call,
        f" <b>إدارة الاشتراك الإجباري</b>\n\n"
        f" الخطط: <b>{len(plans)}</b>\n"
        f"⏳ طلبات معلقة: <b>{len(pending)}</b>",
        kb.admin_subscriptions_keyboard(plans))

@bot.callback_query_handler(func=lambda c: c.data == "adm_sub_add")
def cb_adm_sub_add(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    set_state(call.from_user.id, "adm_sub_add")
    edit(call,
        " <b>إضافة خطة اشتراك جديدة</b>\n\n"
        "أرسل البيانات بهذا الشكل:\n"
        "<code>الاسم|إيموجي|الأيام|نجوم|فودافون|USDT|وصف</code>\n\n"
        "<b>مثال:</b>\n"
        "<code>الباقة الشهرية||30|100|20|2|اشتراك شهري مميز</code>\n\n"
        "<i> ضع 0 لطريقة دفع غير مفعّلة</i>",
        kb.back_keyboard("adm_subscriptions"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_sub_tog_"))
def cb_adm_sub_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    plan_id = int(call.data.split("_")[-1])
    db.toggle_subscription_plan(plan_id)
    bot.answer_callback_query(call.id, " تم التبديل")
    cb_adm_subscriptions(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_sub_del_"))
def cb_adm_sub_del(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    plan_id = int(call.data.split("_")[-1])
    db.delete_subscription_plan(plan_id)
    bot.answer_callback_query(call.id, " تم الحذف")
    cb_adm_subscriptions(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_sub_requests")
def cb_adm_sub_requests(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    requests_list = db.get_pending_subscription_requests()
    if not requests_list:
        edit(call, " <b>طلبات الاشتراك</b>\n\n<i>لا توجد طلبات معلقة.</i>",
             kb.back_keyboard("adm_subscriptions"))
        return
    text = f" <b>طلبات الاشتراك المعلقة ({len(requests_list)})</b>\n\n"
    for r in requests_list[:10]:
        method_names = {"stars": " نجوم", "vodafone": " فودافون كاش", "usdt": " USDT"}
        mname = method_names.get(r["method"], r["method"])
        text += (f" #{r['id']} | {r['plan_emoji']} {r['plan_name']}\n"
                 f" <code>{r['user_id']}</code>  {r['full_name'] or ''}\n"
                 f" {mname}\n"
                 f" {r['proof'][:50] if r['proof'] else ''}\n\n")
    edit(call, text, kb.admin_sub_requests_keyboard(requests_list))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_sub_ok_"))
def cb_adm_sub_ok(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rid = int(call.data.split("_")[-1])
    r = db.get_subscription_request(rid)
    if not r:
        bot.answer_callback_query(call.id, " الطلب غير موجود"); return
    plan = db.get_subscription_plan(r["plan_id"])
    if not plan:
        bot.answer_callback_query(call.id, " الخطة غير موجودة"); return
    from datetime import timedelta
    end_date = (datetime.now() + timedelta(days=plan["duration_days"])).strftime("%Y-%m-%d")
    db.create_subscription(r["user_id"], r["plan_id"], r["method"], end_date, r["proof"])
    db.update_subscription_request_status(rid, "approved", "تمت الموافقة من الأدمن")
    bot.answer_callback_query(call.id, f" تم قبول اشتراك #{rid}")
    try:
        bot.send_message(r["user_id"],
            f" <b>تم قبول اشتراكك!</b>\n\n"
            f"{plan['emoji']} <b>{plan['name']}</b>\n"
            f" ينتهي: <b>{end_date}</b>\n\n"
            f" أهلاً بك في الاشتراك المميز!")
    except Exception: pass
    cb_adm_sub_requests(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_sub_rej_"))
def cb_adm_sub_rej(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    rid = int(call.data.split("_")[-1])
    r = db.get_subscription_request(rid)
    if not r:
        bot.answer_callback_query(call.id, " الطلب غير موجود"); return
    db.update_subscription_request_status(rid, "rejected", "تم الرفض من الأدمن")
    bot.answer_callback_query(call.id, f" تم رفض الطلب #{rid}")
    try:
        bot.send_message(r["user_id"],
            f" <b>تم رفض طلب الاشتراك #{rid}</b>\n\n"
            f"تواصل مع الدعم لمعرفة السبب.")
    except Exception: pass
    cb_adm_sub_requests(call)

# 
#   لوحة الأدمن  تسميات الأزرار
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_button_labels")
def cb_adm_button_labels(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    buttons = db.get_all_button_labels()
    edit(call,
        f" <b>إدارة تسميات الأزرار</b>\n\n"
        f"يمكنك تغيير اسم أي زر أو إخفاؤه/إظهاره\n\n"
        f"<i> = ظاهر |  = مخفي</i>",
        kb.admin_button_labels_keyboard(buttons))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_btn_vis_"))
def cb_adm_btn_vis(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    btn_key = call.data.replace("adm_btn_vis_", "")
    db.toggle_button_visibility(btn_key)
    bot.answer_callback_query(call.id, " تم التبديل")
    cb_adm_button_labels(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_btn_edit_"))
def cb_adm_btn_edit(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    btn_key = call.data.replace("adm_btn_edit_", "")
    r = db.get_button_label(btn_key)
    set_state(call.from_user.id, "adm_btn_edit", btn_key=btn_key)
    edit(call,
        f" <b>تعديل الزر: <code>{btn_key}</code></b>\n\n"
        f"الحالي: <b>{r['btn_emoji']} {r['btn_text']}</b>\n\n"
        f"أرسل الاسم الجديد (مع إيموجي اختياري):\n"
        f"<code>إيموجي|النص</code>\n\n"
        f"مثال: <code>|اشتراك VIP</code>\n"
        f"أو فقط: <code>اشتراك مميز</code>",
        kb.back_keyboard("adm_button_labels"))

#  التحكم في ألوان الأزرار 
@bot.callback_query_handler(func=lambda c: c.data == "adm_btn_colors")
def cb_adm_btn_colors(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    buttons = db.get_all_button_labels()
    edit(call,
        f" <b>إدارة ألوان الأزرار</b>\n\n"
        f" أزرق = primary\n"
        f" أخضر = success\n"
        f" أحمر = danger\n\n"
        f"اضغط على الزر لتغيير لونه:",
        kb.admin_button_colors_keyboard(buttons))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_btn_color_"))
def cb_adm_btn_color_select(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    btn_key = call.data.replace("adm_btn_color_", "")
    r = db.get_button_label(btn_key)
    if not r:
        bot.answer_callback_query(call.id, " الزر غير موجود"); return
    try:
        cur_color = r["btn_color"] or "primary"
    except Exception:
        cur_color = "primary"
    edit(call,
        f" <b>تغيير لون الزر</b>\n\n"
        f"الزر: <b>{r['btn_emoji']} {r['btn_text']}</b>\n"
        f"اللون الحالي: <b>{cur_color}</b>\n\n"
        f"اختر اللون الجديد:",
        kb.admin_btn_color_keyboard(btn_key, cur_color))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_btn_setcolor_"))
def cb_adm_btn_setcolor(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    # format: adm_btn_setcolor_{btn_key}_{color}
    # اللون هو آخر جزء، والمفتاح هو ما بينهما
    parts = call.data.replace("adm_btn_setcolor_", "").rsplit("_", 1)
    if len(parts) != 2:
        bot.answer_callback_query(call.id, " خطأ"); return
    btn_key, color = parts
    if color not in ("primary", "success", "danger"):
        bot.answer_callback_query(call.id, " لون غير معروف"); return
    db.set_button_color(btn_key, color)
    color_names = {"primary": " أزرق", "success": " أخضر", "danger": " أحمر"}
    bot.answer_callback_query(call.id, f" تم تغيير اللون إلى {color_names[color]}")
    # رجّع لصفحة ألوان الأزرار
    buttons = db.get_all_button_labels()
    edit(call,
        f" <b>إدارة ألوان الأزرار</b>\n\n"
        f" أزرق = primary\n أخضر = success\n أحمر = danger\n\n"
        f"اضغط على الزر لتغيير لونه:",
        kb.admin_button_colors_keyboard(buttons))

# 
#   إعداد رقم فودافون كاش (للأدمن)
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_vodafone_number")
def cb_adm_vodafone_number(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cur = db.get_config("vodafone_number", "غير محدد")
    set_state(call.from_user.id, "adm_set_vodafone_number")
    edit(call,
        f" <b>رقم فودافون كاش</b>\n\nالحالي: <code>{cur}</code>\n\nأرسل الرقم الجديد:",
        kb.back_keyboard("adm_charge_settings"))

# 
#   تشغيل / إيقاف البوت (أدمن)
# 
@bot.callback_query_handler(func=lambda c: c.data == "adm_bot_toggle")
def cb_adm_bot_toggle(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    current = db.get_config("bot_active", "1")
    if current == "1":
        db.set_config("bot_active", "0")
        bot.answer_callback_query(call.id, "🔴 تم إيقاف البوت", show_alert=True)
        # إشعار جميع الأدمنية
        all_admins = list(config.ADMIN_IDS)
        try:
            dyn = db.get_dynamic_admins()
            all_admins += [a["tg_id"] for a in dyn if a["tg_id"] not in all_admins]
        except Exception: pass
        for adm_id in all_admins:
            try:
                bot.send_message(adm_id,
                    f"🔴 <b>تم إيقاف البوت مؤقتاً</b>\n"
                    f"من قِبَل: {call.from_user.full_name} (<code>{call.from_user.id}</code>)\n\n"
                    f"المستخدمون لن يتمكنوا من استخدام البوت حتى يتم التشغيل مجدداً.",
                    parse_mode="HTML")
            except Exception: pass
    else:
        db.set_config("bot_active", "1")
        bot.answer_callback_query(call.id, "🟢 تم تشغيل البوت", show_alert=True)
        all_admins = list(config.ADMIN_IDS)
        try:
            dyn = db.get_dynamic_admins()
            all_admins += [a["tg_id"] for a in dyn if a["tg_id"] not in all_admins]
        except Exception: pass
        for adm_id in all_admins:
            try:
                bot.send_message(adm_id,
                    f"🟢 <b>تم تشغيل البوت</b>\n"
                    f"من قِبَل: {call.from_user.full_name} (<code>{call.from_user.id}</code>)",
                    parse_mode="HTML")
            except Exception: pass
    # تحديث لوحة الأدمن لتعكس الحالة الجديدة
    try:
        edit(call,
            f"⚙️ <b>لوحة الأدمن</b>\n\nحالة البوت: {'🟢 يعمل' if db.get_config('bot_active','1') == '1' else '🔴 موقوف'}",
            kb.admin_main_keyboard())
    except Exception: pass

# 
#   خدمة خلفية: تتبع التقدم من القناة الحقيقية
# 
def _notify_orders_channel(order, status_text):
    orders_ch = db.get_config("orders_channel")
    if not orders_ch:
        return
    try:
        bot.send_message(
            orders_ch,
            f"<b>تحديث طلب #{order['id']}</b>\n"
            f"- المستخدم: <code>{order['user_id']}</code>\n"
            f"- الخدمة: {order['service_name']}\n"
            f"- الكمية: {order['quantity']:,}\n"
            f"- الحالة: {status_text}",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"[orders_channel error] {e}")

def _get_real_member_count(link: str) -> int:
    """يجيب عدد أعضاء القناة الحقيقي من تليجرام - يجرب بأشكال مختلفة للرابط"""
    # تحويل رابط t.me إلى @username
    chat_identifier = link
    if "t.me/" in link:
        part = link.split("t.me/")[-1].split("?")[0].strip("/")
        chat_identifier = f"@{part}" if not part.startswith("+") else link
    try:
        result = bot.get_chat_member_count(chat_identifier)
        return result
    except Exception as e:
        print(f"[get_member_count error] link={link} identifier={chat_identifier} | {e}")
        # محاولة بديلة: جلب الـ chat_id الرقمي أولاً
        try:
            chat_obj = bot.get_chat(chat_identifier)
            return bot.get_chat_member_count(chat_obj.id)
        except Exception as e2:
            print(f"[get_member_count fallback error] {e2}")
            return -1

# 
#   نظام التتبع الجديد  thread مستقل لكل طلب
# 

# سجل الـ threads الشغّالة: {order_id: Thread}
_order_threads: dict = {}
_order_threads_lock = threading.Lock()

MILESTONES = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
CHECK_INTERVAL = 30     # 30 ثانية بين كل فحص - يمنع الإشعارات المبكرة
RETRY_DELAY    = 10     # 10 ثواني لو فشل جلب العدد

def _track_single_order(order_id: int):
    """
    يتتبع طلب واحد في thread خاص بيه - أسرع ما يمكن.
    - يفحص عدد الأعضاء باستمرار بدون أي توقف
    - الإشعارات تُرسل في thread منفصل عشان ما توقف الفحص
    - يكتشف التغيير فور حصوله
    """
    print(f"[tracker] بدأ تتبع طلب #{order_id}")

    # ─── جلب بيانات الطلب الثابتة مرة واحدة ───
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()

    if not order:
        print(f"[tracker #{order_id}] الطلب غير موجود")
        return

    link    = order["link"]
    qty     = int(order["quantity"])
    user_id = order["user_id"]
    ch_display = link.replace("https://t.me/", "@").replace("http://t.me/", "@")
    if not ch_display.startswith("@") and not ch_display.startswith("-"):
        ch_display = "@" + ch_display.lstrip("@")

    # ─── جلب start_members ───
    raw_start = order["start_members"] if "start_members" in order.keys() else -1
    if raw_start is None or int(raw_start) < 0:
        try:
            conn_fb = sqlite3.connect(config.DB_PATH)
            conn_fb.row_factory = sqlite3.Row
            fb = conn_fb.execute("SELECT start_members FROM order_progress WHERE order_id=?", (order_id,)).fetchone()
            conn_fb.close()
            if fb and fb["start_members"] is not None and int(fb["start_members"]) >= 0:
                raw_start = int(fb["start_members"])
        except Exception:
            pass
    if raw_start is None or int(raw_start) < 0:
        # جلب طارئ مع retry
        while True:
            fresh = _get_real_member_count(link)
            if fresh >= 0:
                db.set_order_start_members(order_id, fresh)
                raw_start = fresh
                print(f"[tracker #{order_id}] start_members طارئ = {fresh}")
                break
            print(f"[tracker #{order_id}] فشل جلب start_members، إعادة محاولة خلال {RETRY_DELAY}ث")
            time.sleep(RETRY_DELAY)

    start    = int(raw_start)
    last_pct = db.get_order_progress(order_id)

    def _send_notify(text, uid):
        """إرسال إشعار في thread منفصل عشان ما يوقف الفحص"""
        try:
            bot.send_message(uid, text, parse_mode="HTML")
        except Exception as e:
            print(f"[tracker #{order_id}] فشل إرسال إشعار: {e}")

    # ─── حلقة الفحص - بدون أي sleep ───
    consecutive_fails = 0
    while True:
        try:
            # تحقق سريع من حالة الطلب كل 10 فحصات فقط (توفيراً لـ DB)
            if consecutive_fails == 0:
                conn2 = sqlite3.connect(config.DB_PATH)
                conn2.row_factory = sqlite3.Row
                row = conn2.execute(
                    "SELECT status, notified_done FROM orders WHERE id=?", (order_id,)
                ).fetchone()
                conn2.close()
                if not row or row["status"] not in ("pending", "inprogress") or int(row["notified_done"] or 0):
                    print(f"[tracker #{order_id}] انتهى التتبع (الحالة: {row['status'] if row else 'غير موجود'})")
                    break

            # ─── جلب العدد الحالي من تليجرام ───
            current = _get_real_member_count(link)
            if current < 0:
                consecutive_fails += 1
                if consecutive_fails >= 3:
                    # فشل متكرر - انتظر قليلاً
                    time.sleep(RETRY_DELAY)
                    consecutive_fails = 0
                continue

            consecutive_fails = 0
            added = max(0, current - start)
            pct   = min(int((added / qty) * 100), 100) if qty > 0 else 0

            # ─── إشعارات التقدم (فقط لو تغير الـ pct) ───
            if pct > last_pct:
                print(f"[tracker #{order_id}] start={start} current={current} added={added}/{qty} = {pct}%")
                for milestone in sorted(MILESTONES):  # مرتبة تصاعدياً لضمان الترتيب
                    if pct >= milestone > last_pct:
                        added_at_ms = int(qty * milestone / 100)
                        msg_text = (
                            f"<b>تقدم طلبك #{order_id}</b>\n"
                            f"- نسبة الاكتمال: <b>{milestone}%</b>\n"
                            f"- تم اضافة <b>{added_at_ms:,}</b> عضو حتى الآن\n"
                            f"- العدد المطلوب: <b>{qty:,}</b> عضو\n"
                            f"- القناة: <code>{ch_display}</code>"
                        )
                        # إرسال مباشر (بدون thread منفصل) لضمان الترتيب الصحيح
                        _send_notify(msg_text, user_id)
                        print(f"[tracker #{order_id}] إشعار {milestone}% → {user_id}")
                        db.set_order_notified_pct(order_id, milestone)
                        last_pct = milestone

                # ─── اكتمال 100% ───
                if pct >= 100:
                    db.update_order_status(order_id, "completed")
                    completion_text = (
                        f"<b>اكتمل تمويل قناتك!</b>\n\n"
                        f"- القناة: <code>{ch_display}</code>\n"
                        f"- تم اضافة <b>{qty:,}</b> عضو بنجاح\n\n"
                        f"يرجى عدم إزالة البوت من القناة لضمان عدم مغادرة الأعضاء."
                    )
                    threading.Thread(target=_send_notify, args=(completion_text, user_id), daemon=True).start()
                    db.mark_order_notified(order_id)

                    try:
                        conn3 = db.get_conn()
                        u = conn3.execute(
                            "SELECT full_name, username FROM users WHERE tg_id=?", (user_id,)
                        ).fetchone()
                        conn3.close()
                        uname = (u["full_name"] or u["username"] or str(user_id)) if u else str(user_id)
                        db.add_completed_funding(
                            title=ch_display, description=f" {uname}",
                            emoji="", members=qty, channel_url=link,
                        )
                    except Exception as e:
                        print(f"[tracker #{order_id}] add_completed_funding error: {e}")

                    _notify_orders_channel(order, completion_text[:120])
                    print(f"[tracker #{order_id}] اكتمل الطلب - انتهى التتبع")
                    break

        except Exception as e:
            print(f"[tracker #{order_id}] خطأ: {e}")
            time.sleep(RETRY_DELAY)

        # انتظر CHECK_INTERVAL ثانية قبل الفحص التالي
        if CHECK_INTERVAL > 0:
            time.sleep(CHECK_INTERVAL)

    # تنظيف
    with _order_threads_lock:
        _order_threads.pop(order_id, None)
    print(f"[tracker] انتهى thread الطلب #{order_id}")

def _ensure_order_tracked(order_id: int):
    """يتأكد إن في thread شغّال لهذا الطلب  لو مفيش يعمل واحد جديد"""
    with _order_threads_lock:
        t = _order_threads.get(order_id)
        if t and t.is_alive():
            return  # شغّال بالفعل
        # أنشئ thread جديد
        t = threading.Thread(
            target=_track_single_order,
            args=(order_id,),
            daemon=True,
            name=f"tracker-order-{order_id}"
        )
        _order_threads[order_id] = t
        t.start()
        print(f"[tracker]  أُنشئ thread جديد للطلب #{order_id}")

def orders_watchdog():
    """
    Watchdog يشتغل كل 30 ثانية:
    - يجيب كل الطلبات النشطة من DB
    - يتأكد إن كل طلب عنده thread شغّال
    - لو thread مات (crash) يعيد تشغيله تلقائياً
    """
    print("[watchdog]  بدأ Watchdog")
    while True:
        try:
            conn = sqlite3.connect(config.DB_PATH)
            conn.row_factory = sqlite3.Row
            orders = conn.execute(
                "SELECT id FROM orders WHERE status IN ('pending','inprogress') AND notified_done=0"
            ).fetchall()
            conn.close()

            for row in orders:
                _ensure_order_tracked(row["id"])

            # تنظيف threads الميتة من السجل
            with _order_threads_lock:
                dead = [oid for oid, t in _order_threads.items() if not t.is_alive()]
                for oid in dead:
                    _order_threads.pop(oid, None)

        except Exception as e:
            print(f"[watchdog] خطأ: {e}")

        time.sleep(2)  # watchdog كل 2 ثانية بدل 5

#  إيموجي مميزة للأزرار  handlers 

@bot.callback_query_handler(func=lambda c: c.data == "adm_btn_emojis")
def cb_adm_btn_emojis(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    total = len(db.list_btn_emojis())
    edit(call,
        "<b> رموز تعبيرية مميزة للأزرار</b>\n\n"
        "تقدر تحط <b>Custom Emoji ID</b> لأي زر في البوت.\n"
        "الـ ID لازم يكون من إيموجي مميز خاص بـ Telegram Premium.\n\n"
        f"عدد الأزرار المضبوط لها رموز حالياً: <b>{total}</b>",
        kb.admin_btn_emojis_main(total))

@bot.callback_query_handler(func=lambda c: c.data == "adm_btn_emo_groups")
def cb_adm_btn_emo_groups(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    edit(call, "<b> اختر القسم</b>\n\nاختر مجموعة الأزرار:", kb.admin_btn_emojis_groups())

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_btn_emo_g_"))
def cb_adm_btn_emo_group(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    try:
        rest = call.data[len("adm_btn_emo_g_"):]
        gidx_s, page_s = rest.split("_", 1)
        gidx, page = int(gidx_s), int(page_s)
    except Exception:
        bot.answer_callback_query(call.id, "خطأ"); return
    if gidx < 0 or gidx >= len(STATIC_BUTTON_REGISTRY):
        bot.answer_callback_query(call.id, "غير موجود"); return
    name, items = STATIC_BUTTON_REGISTRY[gidx]
    set_count = sum(1 for k, _ in items if db.list_btn_emojis().get(k))
    edit(call,
         f"<b> {name}</b>\n\nإجمالي: <b>{len(items)}</b> | مضبوط: <b>{set_count}</b>\n\nاضغط زر لتعديل رمزه:",
         kb.admin_btn_emojis_group(gidx, page))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_btn_emo_e:"))
def cb_adm_btn_emo_edit(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cb = call.data[len("adm_btn_emo_e:"):]
    if not cb: bot.answer_callback_query(call.id, "خطأ"); return
    label = _label_for_cb(cb)
    cur = db.get_btn_emoji(cb)
    cur_txt = f"<code>{cur}</code>" if cur else "<i>غير مضبوط</i>"
    edit(call,
         f"<b> إيموجي زر: {label}</b>\n\n"
         f"المعرّف: <code>{cb}</code>\nالرمز الحالي: {cur_txt}",
         kb.admin_btn_emoji_edit(cb))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_btn_emo_set:"))
def cb_adm_btn_emo_set(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cb = call.data[len("adm_btn_emo_set:"):]
    if not cb: bot.answer_callback_query(call.id, "خطأ"); return
    set_state(call.from_user.id, "adm_btn_emo_input", target_cb=cb)
    label = _label_for_cb(cb)
    edit(call,
         f"<b>✏️ ضبط إيموجي للزر: {label}</b>\n\n"
         f"أرسل <b>الإيموجي المميز مباشرة</b> من لوحة الإيموجي الخاصة بك ✨\n"
         f"أو أرسل الـ <b>Custom Emoji ID</b> كأرقام فقط.\n\n"
         f"أرسل <code>cancel</code> للإلغاء.",
         kb.back(f"adm_btn_emo_e:{cb}"))

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_btn_emo_clr:"))
def cb_adm_btn_emo_clr(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    cb = call.data[len("adm_btn_emo_clr:"):]
    if not cb: bot.answer_callback_query(call.id, "خطأ"); return
    db.set_btn_emoji(cb, "")
    _invalidate_btn_emoji_cache()
    bot.answer_callback_query(call.id, "تم حذف الرمز")
    call.data = f"adm_btn_emo_e:{cb}"
    cb_adm_btn_emo_edit(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_btn_emo_clear_all")
def cb_adm_btn_emo_clear_all(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    db.clear_all_btn_emojis()
    _invalidate_btn_emoji_cache()
    bot.answer_callback_query(call.id, "تم مسح كل الرموز")
    cb_adm_btn_emojis(call)

@bot.callback_query_handler(func=lambda c: c.data == "adm_btn_emo_help")
def cb_adm_btn_emo_help(call: CallbackQuery):
    if not is_admin(call.from_user.id): return
    edit(call,
         "<b> مساعدة  الإيموجي المميز</b>\n\n"
         "الـ <b>Custom Emoji ID</b> هو رقم طويل خاص بكل إيموجي بريميوم.\n\n"
         "<b>طريقة الحصول عليه:</b>\n"
         "1⃣ ابعت الإيموجي المميز لبوت زي <code>@idstickerbot</code>\n"
         "2⃣ هتلاقي الرد فيه رقم طويل  ده الـ ID\n\n"
         "<b>متطلبات:</b> البوت مالكه عنده Premium أو متفعل على يوزر مدفوع من Fragment ",
         kb.back("adm_btn_emojis"))

# 
#   إدارة قاعدة البيانات من لوحة الأدمن
# 

def _is_admin_check(uid):
    return is_admin(uid)

def _db_table_info():
    """جلب معلومات كل الجداول من قاعدة البيانات"""
    conn = db.get_conn()
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    result = {}
    for t in tables:
        name = t["name"]
        count = conn.execute(f"SELECT COUNT(*) FROM [{name}]").fetchone()[0]
        result[name] = count
    conn.close()
    return result

def _db_table_rows(table, limit=20, offset=0):
    """جلب صفوف من جدول معين"""
    conn = db.get_conn()
    try:
        rows = conn.execute(f"SELECT * FROM [{table}] LIMIT ? OFFSET ?", (limit, offset)).fetchall()
        total = conn.execute(f"SELECT COUNT(*) FROM [{table}]").fetchone()[0]
        conn.close()
        return rows, total
    except Exception as e:
        conn.close()
        return [], 0

def _db_delete_row(table, row_id, id_col="id"):
    """حذف صف من جدول"""
    conn = db.get_conn()
    try:
        conn.execute(f"DELETE FROM [{table}] WHERE [{id_col}]=?", (row_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        conn.close()
        return False

def _db_execute_sql(sql):
    """تنفيذ SQL مخصص (للأدمن فقط)"""
    conn = db.get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql)
        conn.commit()
        rows = cur.fetchall()
        conn.close()
        return True, rows, ""
    except Exception as e:
        conn.close()
        return False, [], str(e)

#  keyboard لوحة إدارة DB 
def kb_db_main():
    m = InlineKeyboardMarkup()
    m.row(InlineKeyboardButton(" عرض الجداول", callback_data="db_show_tables"))
    m.row(InlineKeyboardButton(" تشغيل SQL", callback_data="db_run_sql"))
    m.row(InlineKeyboardButton(" تصدير JSON", callback_data="db_export_json"))
    m.row(InlineKeyboardButton(" استيراد JSON", callback_data="db_import_json"))
    m.row(InlineKeyboardButton(" مسح جدول", callback_data="db_clear_table"))
    m.row(InlineKeyboardButton(" رجوع للوحة", callback_data="adm_back"))
    return m

def kb_db_tables(tables_info):
    m = InlineKeyboardMarkup()
    for name, count in list(tables_info.items())[:20]:
        m.row(InlineKeyboardButton(f" {name} ({count})", callback_data=f"db_table_{name}"))
    m.row(InlineKeyboardButton(" رجوع", callback_data="db_main"))
    return m

def kb_db_table_nav(table, offset, total, limit=10):
    m = InlineKeyboardMarkup()
    nav = []
    if offset > 0:
        nav.append(InlineKeyboardButton(" السابق", callback_data=f"db_tbl_{table}_{max(0,offset-limit)}"))
    if offset + limit < total:
        nav.append(InlineKeyboardButton("التالي ", callback_data=f"db_tbl_{table}_{offset+limit}"))
    if nav:
        m.row(*nav)
    m.row(InlineKeyboardButton(" حذف صف بـ ID", callback_data=f"db_delrow_{table}"))
    m.row(InlineKeyboardButton(" الجداول", callback_data="db_show_tables"))
    m.row(InlineKeyboardButton(" إدارة DB", callback_data="db_main"))
    return m

#  handlers 

@bot.callback_query_handler(func=lambda c: c.data == "db_main")
def cb_db_main(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    edit(call,
        "<b> إدارة قاعدة البيانات</b>\n\n"
        "من هنا تقدر تتحكم كامل في قاعدة البيانات:\n"
        " عرض محتوى أي جدول\n"
        " تشغيل أوامر SQL مباشرة\n"
        " تصدير واستيراد البيانات\n"
        " حذف صفوف معينة",
        kb_db_main())

@bot.callback_query_handler(func=lambda c: c.data == "db_show_tables")
def cb_db_show_tables(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    tables = _db_table_info()
    total_records = sum(tables.values())
    text = (f"<b> جداول قاعدة البيانات</b>\n\n"
            f"عدد الجداول: <b>{len(tables)}</b>\n"
            f"إجمالي السجلات: <b>{total_records:,}</b>\n\n"
            f"اختر جدولاً للعرض:")
    edit(call, text, kb_db_tables(tables))

@bot.callback_query_handler(func=lambda c: c.data.startswith("db_table_") and not c.data.startswith("db_tbl_"))
def cb_db_table_view(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    table = call.data[len("db_table_"):]
    _show_table_page(call, table, 0)

@bot.callback_query_handler(func=lambda c: c.data.startswith("db_tbl_"))
def cb_db_table_nav(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    parts = call.data[len("db_tbl_"):].rsplit("_", 1)
    if len(parts) != 2:
        bot.answer_callback_query(call.id, "خطأ")
        return
    table, offset = parts[0], int(parts[1])
    _show_table_page(call, table, offset)

def _show_table_page(call, table, offset, limit=10):
    rows, total = _db_table_rows(table, limit, offset)
    if total == 0:
        edit(call,
            f"<b> {table}</b>\n\n<i>الجدول فارغ</i>",
            kb_db_table_nav(table, offset, total, limit))
        return
    text = f"<b> {table}</b>\n"
    text += f"السجلات: <b>{total:,}</b> | يعرض: {offset+1}{min(offset+limit, total)}\n"
    text += "\n"
    for i, row in enumerate(rows):
        row_dict = dict(row) if row else {}
        row_str = " | ".join(f"{k}: {v}" for k, v in list(row_dict.items())[:4])
        text += f"<code>{row_str}</code>\n"
        if len(text) > 3500:
            text += f"\n<i>... و {len(rows)-i-1} صف آخر</i>"
            break
    edit(call, text, kb_db_table_nav(table, offset, total, limit))

@bot.callback_query_handler(func=lambda c: c.data.startswith("db_delrow_"))
def cb_db_delrow(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    table = call.data[len("db_delrow_"):]
    set_state(call.from_user.id, "db_delrow_input", table=table)
    edit(call,
        f"<b> حذف صف من جدول: {table}</b>\n\n"
        f"أرسل رقم الـ ID للصف الذي تريد حذفه.\n"
        f"<i>أرسل cancel للإلغاء</i>",
        InlineKeyboardMarkup([[InlineKeyboardButton(" إلغاء", callback_data=f"db_table_{table}")]]))

@bot.message_handler(func=lambda m: get_state(m.from_user.id).get("state") == "db_delrow_input")
def msg_db_delrow(msg: Message):
    if not _is_admin_check(msg.from_user.id): return
    if msg.text.strip().lower() == "cancel":
        clear_state(msg.from_user.id)
        send(msg.chat.id, " تم الإلغاء")
        return
    d = get_state(msg.from_user.id).get("data", {})
    table = d.get("table", "")
    try:
        row_id = int(msg.text.strip())
    except ValueError:
        send(msg.chat.id, " أرسل رقم صحيح فقط!")
        return
    ok = _db_delete_row(table, row_id)
    clear_state(msg.from_user.id)
    if ok:
        send(msg.chat.id, f" تم حذف الصف #{row_id} من جدول {table}")
    else:
        send(msg.chat.id, f" فشل الحذف  تأكد من الـ ID")

@bot.callback_query_handler(func=lambda c: c.data == "db_run_sql")
def cb_db_run_sql(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    set_state(call.from_user.id, "db_sql_input")
    edit(call,
        "<b> تشغيل SQL مباشر</b>\n\n"
        " <b>تحذير:</b> هذه الأداة للمستخدمين المتقدمين فقط!\n"
        "أي خطأ قد يؤثر على قاعدة البيانات.\n\n"
        "أرسل أمر SQL كاملاً:\n"
        "<i>مثال: SELECT * FROM users LIMIT 5</i>\n\n"
        "<i>أرسل cancel للإلغاء</i>",
        InlineKeyboardMarkup([[InlineKeyboardButton(" إلغاء", callback_data="db_main")]]))

@bot.message_handler(func=lambda m: get_state(m.from_user.id).get("state") == "db_sql_input")
def msg_db_sql(msg: Message):
    if not _is_admin_check(msg.from_user.id): return
    if msg.text.strip().lower() == "cancel":
        clear_state(msg.from_user.id)
        send(msg.chat.id, " تم الإلغاء")
        return
    sql = msg.text.strip()
    clear_state(msg.from_user.id)
    ok, rows, err = _db_execute_sql(sql)
    if not ok:
        send(msg.chat.id, f" <b>خطأ SQL:</b>\n<code>{err}</code>")
        return
    if rows:
        result_text = f" <b>نتيجة SQL</b>\n<code>{sql[:100]}</code>\n\n"
        for i, row in enumerate(rows[:15]):
            row_dict = dict(row) if hasattr(row, 'keys') else {}
            row_str = " | ".join(f"{k}: {v}" for k, v in list(row_dict.items())[:5])
            result_text += f"<code>{row_str}</code>\n"
            if len(result_text) > 3500:
                result_text += f"<i>... و {len(rows)-i-1} صف آخر</i>"
                break
        if len(rows) > 15:
            result_text += f"\n<i>إجمالي: {len(rows)} صف</i>"
    else:
        result_text = f" <b>تم تنفيذ الأمر بنجاح</b>\n<code>{sql[:200]}</code>"
    send(msg.chat.id, result_text,
        InlineKeyboardMarkup([[InlineKeyboardButton(" إدارة DB", callback_data="db_main")]]))

@bot.callback_query_handler(func=lambda c: c.data == "db_export_json")
def cb_db_export_json(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    bot.answer_callback_query(call.id, "⏳ جاري التصدير...")
    try:
        json_data = db.export_db_json()
        import io
        file_obj = io.BytesIO(json_data.encode("utf-8"))
        file_obj.name = "db_backup.json"
        bot.send_document(
            call.message.chat.id,
            file_obj,
            caption=" <b>تصدير قاعدة البيانات</b>\n\nتم تصدير الإعدادات بنجاح "
        )
    except Exception as e:
        bot.send_message(call.message.chat.id, f" خطأ في التصدير: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "db_import_json")
def cb_db_import_json(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    set_state(call.from_user.id, "db_import_input")
    edit(call,
        "<b> استيراد قاعدة البيانات</b>\n\n"
        "أرسل ملف JSON الذي تريد استيراده.\n"
        " سيتم استبدال البيانات الحالية!\n\n"
        "<i>أرسل cancel للإلغاء</i>",
        InlineKeyboardMarkup([[InlineKeyboardButton(" إلغاء", callback_data="db_main")]]))

@bot.message_handler(content_types=["document"],
                     func=lambda m: get_state(m.from_user.id).get("state") == "db_import_input")
def msg_db_import(msg: Message):
    if not _is_admin_check(msg.from_user.id): return
    clear_state(msg.from_user.id)
    try:
        file_info = bot.get_file(msg.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        json_str = downloaded.decode("utf-8")
        ok, result_msg = db.import_db_json(json_str)
        if ok:
            send(msg.chat.id, f" <b>تم الاستيراد بنجاح!</b>\n{result_msg}")
        else:
            send(msg.chat.id, f" <b>فشل الاستيراد:</b>\n{result_msg}")
    except Exception as e:
        send(msg.chat.id, f" خطأ: {e}")

@bot.callback_query_handler(func=lambda c: c.data == "db_clear_table")
def cb_db_clear_table(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    tables = _db_table_info()
    m = InlineKeyboardMarkup()
    for name in list(tables.keys())[:15]:
        m.row(InlineKeyboardButton(f" {name}", callback_data=f"db_clear_confirm_{name}"))
    m.row(InlineKeyboardButton(" رجوع", callback_data="db_main"))
    edit(call,
        "<b> مسح جدول</b>\n\n"
        " <b>تحذير: هذه العملية لا يمكن التراجع عنها!</b>\n\n"
        "اختر الجدول الذي تريد مسح محتوياته:",
        m)

@bot.callback_query_handler(func=lambda c: c.data.startswith("db_clear_confirm_"))
def cb_db_clear_confirm(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    table = call.data[len("db_clear_confirm_"):]
    m = InlineKeyboardMarkup()
    m.row(
        InlineKeyboardButton(" نعم، امسح", callback_data=f"db_clear_do_{table}"),
        InlineKeyboardButton(" إلغاء", callback_data="db_clear_table")
    )
    edit(call,
        f" <b>تأكيد المسح</b>\n\n"
        f"هل أنت متأكد من مسح كل بيانات جدول:\n"
        f"<b>{table}</b>؟\n\n"
        f"<i>هذه العملية لا يمكن التراجع عنها!</i>",
        m)

@bot.callback_query_handler(func=lambda c: c.data.startswith("db_clear_do_"))
def cb_db_clear_do(call: CallbackQuery):
    if not _is_admin_check(call.from_user.id): return
    table = call.data[len("db_clear_do_"):]
    # حماية الجداول الأساسية
    protected = {"users", "config"}
    if table in protected:
        bot.answer_callback_query(call.id, f" لا يمكن مسح جدول {table}  محمي", show_alert=True)
        return
    ok, _, err = _db_execute_sql(f"DELETE FROM [{table}]")
    if ok:
        bot.answer_callback_query(call.id, f" تم مسح جدول {table}")
        cb_db_main(call)
    else:
        bot.answer_callback_query(call.id, f" خطأ: {err}", show_alert=True)

if __name__ == "__main__":
    print(f" {config.BOT_NAME} V5 يعمل الآن...")
    print(" نظام تتبع جديد: thread مستقل لكل طلب + watchdog تلقائي")
    print(" يتطلب pyTelegramBotAPI >= 4.32")

    # شغّل الـ watchdog في خلفية  هو اللي يشغّل threads الطلبات
    threading.Thread(target=orders_watchdog, daemon=True, name="watchdog").start()

    bot.infinity_polling(timeout=60, long_polling_timeout=30)
