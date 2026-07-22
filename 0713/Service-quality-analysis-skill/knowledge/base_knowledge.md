# Ticket (Trouble Ticket) Query Template

> **TT = Trouble Ticket**, i.e., tickets. These are operations handling documents associated with alarms.
>
> **⚠️ `ttcreatetime` and `firstoccurrence` are `BIGINT` Unix ms timestamps** — wrap with `FROM_UNIXTIME(field/1000)` before `DATE()`/`TIMESTAMPDIFF()`.
>
> **Common date filtering**: `DATE(FROM_UNIXTIME(e.ttcreatetime/1000))` or `DATE(FROM_UNIXTIME(a.firstoccurrence/1000))`
> - `today` → `DATE(FROM_UNIXTIME(e.ttcreatetime/1000)) = CURDATE()`
> - `yesterday` → `DATE(FROM_UNIXTIME(e.ttcreatetime/1000)) = DATE_SUB(CURDATE(), INTERVAL 1 DAY)`
> - `date range` → `DATE(FROM_UNIXTIME(e.ttcreatetime/1000)) BETWEEN '{start date}' AND '{end date}'`

## 4.1 Field Enumeration Values

> **ticketstatus (ticket status)**: 0-24, 100, 102, 105 (numeric type, not string)
> **ticketpriority (ticket priority)**: 3, 4, 5 (larger number = higher priority)
### severity (Alarm Severity)

| severity Value | Meaning | Clearance |
|----------------|---------|-----------|
| 0 | Cleared | Yes (closed/clean) |
| 1 | Indeterminate | No (open) |
| 2 | Warning | No (open) |
| 3 | Minor | No (open) |
| 4 | Major | No (open) |
| 5 | Critical | No (open) |

> **TT Open/Closed判断**: `severity = 0` = Closed/Clean, `severity != 0` = Open

### ticketstatus Enumeration Values

| ticketstatus Value | Description |
|-------------------|-------------|
| 0 | Not Created |
| 1 | Creating |
| 2 | Created Successfully |
| 3 | Creation Failed |
| 4 | Pending Auto-Create |
| 5 | Create Immediately |
| 6 | Cancel Creation |
| 7 | Cancelled |
| 8 | Closed |
| 9 | Associating |
| 10 | Association Success |
| 11 | Association Failed |
| 12 | Deleted |
| 13 | Async Creating |
| 14 | Pending Suppression |
| 15 | Suppressed |
| 20 | Created |
| 21 | Dispatched |
| 22 | Processing |
| 23 | Pending |
| 24 | Resolved |
| 100 | Terminated |
| 102 | Completed |
| 105 | Ended |



# Rate Metric Query Template

> Business formulas:
> - **Compression Rate** = Compressed Alarm / Total Alarm
> - **Auto TT Rate** = Auto TT Number / Total TT Number
> - **Alarm Diagnose Rate** = Diagnose Success / Total Diagnosis
> - **RCA Success Rate** = RCA Success / Total Alarm

> **Common date filtering**: use `DATE(FROM_UNIXTIME(e.ttcreatetime/1000))` or `DATE(FROM_UNIXTIME(a.firstoccurrence/1000))`
> - ⚠️ `ttcreatetime` and `firstoccurrence` are `BIGINT` Unix ms timestamps, not datetime — must wrap with `FROM_UNIXTIME(field/1000)`.
> - `yesterday` → `DATE_SUB(CURDATE(), INTERVAL 1 DAY)`
> - `last week` → `DATE_SUB(CURDATE(), INTERVAL 7 DAY)`
> - Date range → `BETWEEN DATE_SUB(CURDATE(), INTERVAL 7 DAY) AND CURDATE()`


# Outage Query Template

> **Outage definition**: `sitedownfault IN (1, 6)` in `ap_alarm_live`
> - `1` = access/signaling link down (OML Fault, NodeB Unavailable, Multiple site down)
> - `6` = NE management unreachable (NE Is Disconnected)
>
> **⚠️ `firstoccurrence` and `ttcreatetime` are `BIGINT` Unix ms timestamps** — wrap with `FROM_UNIXTIME(field/1000)` before `TIMESTAMPDIFF()`/`DATE()`.
>
> **Query result sorting**:
> - Results are sorted by `firstoccurrence DESC` (latest first)
> - **Default behavior**: Return only the latest 1 record (add `LIMIT 1`)
> - **If user requests "all" or multiple**: Remove `LIMIT 1` to return all matching outages


# Operations Metrics MTTE/MTTR Template

> **⚠️ Field type warning**: `firstoccurrence`, `cleartime`, `ttcreatetime` are all `BIGINT` Unix **millisecond** timestamps, NOT datetime.
> - Must wrap with `FROM_UNIXTIME(field/1000)` before `DATE()`, `TIMESTAMPDIFF()`, etc.
> - Null check: use `field IS NOT NULL AND field > 0` (not `!= ''`).

> Business formulas:
> - **MTTE** = `ttcreatetime - firstoccurrence` (minutes)
> - **MTTR** = `cleartime - firstoccurrence` (minutes)

