import type { InputType, ParamFilterType, Preset } from "./types";

/* Static option catalogs and presets shared across the workbench UI. */

export const TECHNIQUES = [
  { value: "BESUTQ", label: "全部" },
  { value: "B", label: "布尔盲注" },
  { value: "E", label: "报错注入" },
  { value: "S", label: "堆叠注入" },
  { value: "U", label: "联合注入" },
  { value: "T", label: "时间盲注" },
  { value: "Q", label: "内联查询" },
];

export const DBMS_OPTIONS = [
  "", "Altibase", "Amazon Redshift", "Apache Derby", "Apache Ignite", "Aurora", "ClickHouse",
  "CockroachDB", "CrateDB", "Cubrid", "Drizzle", "EnterpriseDB", "eXtremeDB", "Firebird",
  "FrontBase", "Greenplum", "H2", "HSQLDB", "IBM DB2", "Informix", "InterSystems Cache",
  "Iris", "MariaDB", "Mckoi", "MemSQL", "Microsoft Access", "Microsoft SQL Server", "MimerSQL",
  "MonetDB", "MySQL", "OpenGauss", "Oracle", "Percona", "PostgreSQL", "Presto",
  "Raima Database Manager", "SAP MaxDB", "SQLite", "Sybase", "TiDB", "Vertica", "Virtuoso",
  "Yellowbrick", "YugabyteDB",
];

export const PARAM_FILTER_OPTIONS: Array<{ value: ParamFilterType; label: string }> = [
  { value: "", label: "不限" },
  { value: "GET", label: "GET" },
  { value: "POST", label: "POST" },
  { value: "COOKIE", label: "COOKIE" },
  { value: "USER-AGENT", label: "User-Agent" },
  { value: "REFERER", label: "Referer" },
  { value: "HOST", label: "Host" },
];

export const TAMPER_PRESETS: Record<string, string[]> = {
  "关闭": [],
  "通用绕过": ["between", "randomcase", "space2comment"],
  "编码绕过": ["charencode", "chardoubleencode", "charunicodeencode"],
  "WAF 强化": ["between", "randomcase", "randomcomments", "space2comment", "charencode"],
  "MySQL 定向": ["space2mysqlblank", "space2mysqldash", "versionedkeywords"],
  "MSSQL 定向": ["space2mssqlblank", "space2mssqlhash", "between"],
};

export const PRESETS: Array<{ value: Preset; label: string; description: string }> = [
  { value: "balanced", label: "平衡测试", description: "level 3 / risk 2 / threads 6" },
  { value: "deep", label: "深度测试", description: "level 5 / risk 3 / threads 10" },
  { value: "waf", label: "WAF 绕过", description: "text-only + tamper 组合" },
  { value: "enum_structure", label: "枚举结构", description: "level 3 + dbs + tables" },
  { value: "data_export", label: "数据导出", description: "level 3 + dump-all" },
];

export const INPUT_TYPE_BUTTONS: Array<{ value: InputType; label: string }> = [
  { value: "url", label: "单 URL" },
  { value: "raw_request", label: "原始请求" },
  { value: "batch_urls", label: "批量 URL" },
  { value: "batch_requests", label: "批量请求包" },
];

export const URL_EXAMPLE = "http://127.0.0.1/vul/sqli/sqli_id.php?id=1";

export const REQUEST_EXAMPLE = `POST /vul/sqli/sqli_id.php HTTP/1.1
Host: 127.0.0.1
User-Agent: Mozilla/5.0
Content-Type: application/x-www-form-urlencoded
Cookie: PHPSESSID=test

id=1&submit=查询`;

/** Maximum log lines kept in the DOM at once (full history stays in state). */
export const MAX_RENDERED_LOG_LINES = 2000;
