# QPOD 数据库下载指南

本仓库提供了一套 Python 工具，帮助你从 QPOD 网站批量获取材料 ID，并下载对应的 CIF 文件。以下内容介绍了环境准备、依赖安装以及各脚本的推荐使用顺序。

## 环境准备
- Python 3.9+（建议使用虚拟环境隔离依赖）
- 推荐依赖安装方式：`pip`

### 创建并激活虚拟环境（示例）
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows 请改用 .venv\\Scripts\\activate
```

### 安装所需依赖
需要的第三方库包括 `requests`、`beautifulsoup4` 和可选的 `tqdm`（为下载过程提供进度条）。
```bash
pip install requests beautifulsoup4 tqdm
```
如需固定依赖版本，可自行在 `requirements.txt` 中列出并执行 `pip install -r requirements.txt`。

## 各脚本用途与运行方式
以下步骤假设你已经激活虚拟环境。

### 1. 抓取材料 ID：`download_cif_list.py`
1. 打开脚本，将 `sid = 73` 改成想要抓取的子数据库 ID。
2. 运行：
   ```bash
   python download_cif_list.py
   ```
   - 脚本会遍历指定 `sid` 的分页列表，持续写入 `qpod_sid<sid>_material_ids.txt`。
   - 若文件已存在，脚本会自动跳过已记录的 ID，实现断点续爬。

### 2. 去重材料 ID：`dedup_ids.py`
```bash
python dedup_ids.py
```
- 默认读取 `qpod_sid73_material_ids.txt`，保留首次出现的 ID，并在修改前生成 `.bak` 备份。
- 若你使用不同文件名，可在脚本顶部调整 `IDS_PATH` 与 `BACKUP_PATH`。

### 3. 检查缺失 CIF：`check_cifs.py`
```bash
python check_cifs.py
```
- 读取 ID 列表与 `cif_downloads/` 目录下已有的 `.cif` 文件名，输出缺失和多余的 ID 并写入 `missing_ids.txt`。
- 可修改脚本顶部的 `IDS_FILE`、`CIF_DIR`、`MISSING_FILE` 指向自定义路径。

### 4. 批量下载 CIF：`download_cifs.py`
```bash
python download_cifs.py \
  --ids missing_ids.txt \
  --out cif_downloads \
  --timeout 30 \
  --log download_status.csv \
  --batch-size 5
```
- `--ids`：待下载的材料 ID 列表，默认读取 `missing_ids.txt`。
- `--out`：CIF 输出目录；不存在时会自动创建。
- `--timeout`：单个请求的超时时间（秒）。
- `--log`：下载状态 CSV，会持续追加更新，便于断点续传。
- `--batch-size`：并行下载的线程数，适当调节以平衡速度与稳定性。
- 若安装了 `tqdm`，脚本会显示进度条；否则使用标准输出。

## 其他提示
- 遇到网络波动可多次运行脚本，日志与缺失列表会帮助跳过已下载内容。
- 建议在长时间运行前先用少量 ID 测试，以确认网络和权限配置无误。
- 如需代理、速率限制等高级设置，可在脚本中自定义 `requests.Session` 或下载逻辑。

祝你下载顺利！
