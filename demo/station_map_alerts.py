"""Persistent in-app notifications for the local forecast owner."""

from contextlib import closing
from datetime import datetime, timezone
import sqlite3

from demo.station_map_live import VIETNAM, timestamp


class AdminAlerts:
    def __init__(self, path):
        self.path = path
        with closing(sqlite3.connect(path)) as db, db:
            db.execute('''
                CREATE TABLE IF NOT EXISTS admin_alerts (
                    id INTEGER PRIMARY KEY,
                    incident TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    action TEXT NOT NULL,
                    first_seen_utc TEXT NOT NULL,
                    last_seen_utc TEXT NOT NULL,
                    occurrences INTEGER NOT NULL DEFAULT 1,
                    read_utc TEXT
                )
            ''')

    def add(self, kind, at, title, detail, action, day=None):
        incident = f'{day or at.astimezone(VIETNAM).date()}:{kind}'
        time = at.astimezone(timezone.utc).isoformat(timespec='microseconds')
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('''
                INSERT INTO admin_alerts(incident, title, detail, action, first_seen_utc, last_seen_utc)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(incident) DO UPDATE SET
                    title=excluded.title, detail=excluded.detail, action=excluded.action,
                    last_seen_utc=excluded.last_seen_utc, occurrences=admin_alerts.occurrences+1,
                    read_utc=CASE WHEN admin_alerts.detail=excluded.detail THEN admin_alerts.read_utc ELSE NULL END
                WHERE excluded.last_seen_utc>admin_alerts.last_seen_utc
            ''', (incident, title, detail, action, time, time))

    def inbox(self, summary=False):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            unread = db.execute('SELECT COUNT(*) FROM admin_alerts WHERE read_utc IS NULL').fetchone()[0]
            response = dict(unread=unread)
            if not summary:
                rows = db.execute('''
                    SELECT id, title, detail, action, first_seen_utc, last_seen_utc, occurrences, read_utc
                    FROM admin_alerts ORDER BY read_utc IS NOT NULL, last_seen_utc DESC LIMIT 30
                ''')
                response['items'] = [dict(row) for row in rows]
            return response

    def mark_read(self, identifier=None):
        with closing(sqlite3.connect(self.path)) as db, db:
            now = datetime.now(timezone.utc).isoformat()
            if identifier is None:
                db.execute('UPDATE admin_alerts SET read_utc=? WHERE read_utc IS NULL', (now,))
            else:
                db.execute('UPDATE admin_alerts SET read_utc=? WHERE id=? AND read_utc IS NULL', (now, identifier))

    def sources(self, report):
        sources = report.get('sources', {})
        gfs = sources.get('gfs', {})
        if gfs.get('status') == 'error':
            fields = gfs.get('fields')
            detail = f'Lần kiểm tra tìm được {fields}/19 trường GFS.' if isinstance(fields, int) else 'Chưa đọc được chỉ mục GFS.'
            self.add('gfs', timestamp(gfs['checked_at']), 'GFS chưa đủ trường đầu vào', detail,
                     'Kiểm tra kết nối và giờ công bố chu kỳ GFS 00 UTC. Sau đó kiểm tra nguồn lại.')
        vrain = sources.get('vrain', {})
        channels = vrain.get('channels', {})
        if vrain.get('status') != 'error' and not any(item.get('status') == 'error' for item in channels.values()):
            return
        statuses = [item.get('http_status') for item in channels.values()] or [vrain.get('http_status')]
        if channels:
            def channel_text(key):
                item = channels.get(key, {})
                status = item.get('http_status')
                return f'HTTP {status}' if isinstance(status, int) else 'chưa đọc được'
            detail = f'Kênh hiện tại {channel_text("modern")} · Kênh lịch sử {channel_text("legacy")}.'
        else:
            detail = 'Chưa lấy được mưa giờ tại trạm.'
        inventory_code = vrain.get('inventory_http_status')
        if vrain.get('authorized_group') is True:
            detail += ' Danh mục trạm vẫn xác nhận quyền xem nhóm Đà Nẵng.'
        elif inventory_code in (401, 403):
            detail += f' Kiểm tra phiên đăng nhập trả HTTP {inventory_code}.'
        if inventory_code in (401, 403) or 401 in statuses or 403 in statuses:
            action = 'Kiểm tra phiên đăng nhập và quyền truy cập dữ liệu của tài khoản Vrain.'
        elif 404 in statuses:
            action = 'Xác nhận với Vrain đường xuất mưa giờ dành cho nhóm Đà Nẵng, rồi kiểm tra nguồn lại.'
        else:
            action = 'Kiểm tra dịch vụ Vrain và truyền dữ liệu theo giờ.'
        self.add('vrain', timestamp(vrain['checked_at']), 'Vrain chưa trả đủ dữ liệu mưa giờ', detail, action)

    def job(self, report):
        status = report.get('status')
        job = report.get('job')
        reason = report.get('reason')
        if job == 'forecast':
            available, expected = report.get('stations'), report.get('stations_expected')
            if status == 'recorded' and isinstance(available, int) and isinstance(expected, int) and available < expected:
                title = 'Bản dự báo chỉ có một phần số trạm'
                detail = f'Lượt phát lưu được dự báo cho {available}/{expected} trạm.'
                action = 'Xem các trạm thiếu trong bản đồ và kiểm tra chuỗi mưa giờ trước mốc 18h.'
            elif status in ('blocked', 'failed') or (status == 'skipped' and reason == 'outside_forecast_window'):
                title = 'Chưa ghi được lượt dự báo 19h'
                detail = {
                    'vrain_unavailable': 'Vrain lỗi khi thu lịch sử mưa trạm.',
                    'vrain_18h_pending': 'Mưa trạm tới 18h chưa có đủ trước hạn thu.',
                    'gfs_unavailable': 'Chu kỳ GFS cần thiết chưa đủ trường.',
                    'outside_forecast_window': 'Máy chạy thu dữ liệu sau khung giờ cho lượt này.',
                }.get(reason, 'Luồng lấy dữ liệu hoặc lưu dự báo gặp lỗi.')
                action = 'Xem trạng thái GFS, Vrain và lần chạy gần nhất trong mục Cập nhật hằng ngày.'
            else:
                return
        elif job == 'verify' and status in ('failed', 'pending'):
            title = 'Lượt đến hạn chưa đủ số đo để đối chiếu'
            detail = 'Bước kiểm tra chưa thu được bộ nhãn mưa Vrain hợp lệ.'
            action = 'Kiểm tra nguồn Vrain. Tác vụ đối chiếu sẽ kiểm tra lại ở lượt sau.'
        else:
            return
        at = timestamp(report['finished_utc'])
        day = timestamp(report['issue_utc']).astimezone(VIETNAM).date() if report.get('issue_utc') else None
        self.add(job, at, title, detail, action, day=day)
