import requests
from bs4 import BeautifulSoup
import os
import time
from urllib.parse import urlparse, unquote, urljoin

# 尝试导入 googlesearch 库，如果失败则提示安装
try:
    from googlesearch import search
except ImportError:
    print("错误：缺少 'googlesearch-python' 库。")
    print("请使用以下命令安装:")
    print("pip install googlesearch-python")
    exit()

# 创建一个全局的 Session 对象，或者在主函数中创建并传递
# 在这里，我们选择在主调函数中创建并传递，更清晰
# session = requests.Session() # 如果选择全局方式

def download_pdf(session, url, folder="downloaded_pdfs"):
    """
    从给定的 URL 下载 PDF 文件到指定的文件夹，使用传入的 Session。

    Args:
        session (requests.Session): 用于发起请求的 Session 对象。
        url (str): PDF 文件的 URL.
        folder (str): 保存 PDF 的目标文件夹名称.

    Returns:
        bool: 下载成功返回 True，否则返回 False.
    """
    # 确保目标文件夹存在
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
            print(f"创建文件夹: {folder}")
        except OSError as e:
            print(f"创建文件夹 {folder} 失败: {e}")
            return False

    try:
        # 使用传入的 session 发送 GET 请求下载文件
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'}
        # 将 headers 添加到 session 的 headers 中，这样后续请求会自动使用
        # 或者在 get 请求中单独指定 headers=headers
        session.headers.update(headers)
        response = session.get(url, stream=True, timeout=60, verify=False) # <--- 添加 verify=False
        response.raise_for_status() # 如果状态码不是 200，则抛出异常

        # 从 URL 中提取文件名
        parsed_url = urlparse(url)
        # 使用 unquote 处理 URL 编码的字符（例如 %20）
        filename = os.path.basename(unquote(parsed_url.path))

        # 如果无法从路径提取有效文件名，或者不是以 .pdf 结尾，则尝试从 Content-Disposition 获取
        if not filename or not filename.lower().endswith(".pdf"):
             content_disposition = response.headers.get('Content-Disposition')
             if content_disposition:
                 import re
                 fname = re.findall('filename="?(.+)"?', content_disposition)
                 if fname:
                     filename = unquote(fname[0])

        # 如果仍然没有有效文件名，生成一个基于时间戳的默认名称
        if not filename or not filename.lower().endswith(".pdf"):
            timestamp = int(time.time() * 1000)
            filename = f"downloaded_pdf_{timestamp}.pdf"
            print(f"无法从 URL 或响应头提取有效 PDF 文件名，使用默认名称: {filename}")

        # 确保文件名是合法的
        # 移除或替换可能导致问题的字符（简单处理）
        filename = "".join(c for c in filename if c.isalnum() or c in ('.', '_', '-')).rstrip()
        if not filename.lower().endswith(".pdf"): # 再次检查，防止处理后丢失后缀
             filename += ".pdf"


        filepath = os.path.join(folder, filename)

        print(f"开始下载: {filename} (来自 {url})")
        # 以二进制写模式打开文件，分块写入数据
        with open(filepath, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk: # 过滤掉 keep-alive 新块
                    f.write(chunk)
        print(f"下载完成: {filepath}")
        return True

    except requests.exceptions.Timeout:
        print(f"下载超时: {url}")
        return False
    except requests.exceptions.RequestException as e:
        # 可以在这里更具体地捕获 SSLError，但为了简单起见，保持通用异常处理
        print(f"下载失败 {url}: {e}")
        # 如果是因为 SSL 错误，可以添加特定提示
        if isinstance(e, requests.exceptions.SSLError):
             print("提示：下载失败可能是由于 SSL 证书验证问题。已尝试禁用验证 (verify=False)。")
        return False
    except Exception as e:
        print(f"处理或保存文件时发生未知错误 {url}: {e}")
        return False

def search_and_download_pdfs(query, num_results=50, download_folder="columbia_pdfs"):
    """
    使用 googlesearch 库搜索匹配查询的 PDF 链接并下载它们。

    Args:
        query (str): Google 搜索查询字符串.
        num_results (int): 期望获取的最大搜索结果数量.
        download_folder (str): 下载 PDF 的目标文件夹.
    """
    print(f"开始 Google 搜索: \"{query}\" (最多查找 {num_results} 条结果)")
    pdf_urls = set() # 使用集合来存储 URL，自动去重

    try:
        # 执行搜索，移除 pause 参数
        # lang='en' 可能比 'zh-cn' 返回更多技术性文档结果，可以按需调整
        search_results = search(query, num_results=num_results, lang='en') # <--- 移除 pause=2.5

        for url in search_results:
            # 直接检查 URL 是否以 .pdf 结尾且域名正确
            parsed_link = urlparse(url)
            if url.lower().endswith(".pdf") and "columbiasports.cn" in parsed_link.netloc:
                print(f"发现 PDF 链接: {url}")
                pdf_urls.add(url)
            else:
                 # 有些结果可能是指向包含 PDF 链接的页面，而不是直接指向 PDF
                 # （可选）可以尝试访问这些页面并查找 PDF 链接，但这会增加复杂性和请求次数
                 print(f"忽略非直接 PDF 链接或非目标站点链接: {url}")
                 pass # 当前脚本只处理直接的 PDF 链接

    except Exception as e:
        print(f"Google 搜索过程中发生错误: {e}")
        # 错误提示信息可以保持不变或相应调整
        print("这可能是由于 googlesearch 库的限制、网络问题或被 Google 暂时阻止。")
        # print("可以尝试减少 num_results 或增加 pause 时间。") # 这句可以注释掉或移除

    if not pdf_urls:
        print("在搜索结果中未找到符合条件的 PDF 链接。")
        return

    print(f"\n找到 {len(pdf_urls)} 个唯一的 PDF 链接。准备开始下载...")

    # 在这里创建 Session 对象
    with requests.Session() as session:
        download_count = 0
        total_links = len(pdf_urls)
        for i, pdf_url in enumerate(pdf_urls, 1):
            print(f"\n--- 处理第 {i}/{total_links} 个链接 ---")
            # 将 session 传递给 download_pdf 函数
            if download_pdf(session, pdf_url, folder=download_folder):
                download_count += 1
            # 在每次下载后暂停一下，减少对服务器的压力
            # 注意：这里的 time.sleep 是下载之间的暂停，与搜索无关
            time.sleep(1.5)

    print(f"\n下载过程结束。")
    print(f"总共尝试下载 {total_links} 个链接，成功下载 {download_count} 个 PDF 文件。")
    print(f"文件已保存到 \"{os.path.abspath(download_folder)}\" 文件夹。")


# --- 主程序入口 ---
if __name__ == "__main__":
    # 定义搜索查询
    search_query = "filetype:pdf site:columbiasports.cn"

    # 定义下载文件夹名称
    pdf_download_folder = "columbia_sportswear_pdfs"

    # 定义期望搜索结果的数量（注意：实际返回数量可能少于此值）
    max_search_results = 150 # 可以根据需要调整

    # 调用主函数执行搜索和下载
    search_and_download_pdfs(
        query=search_query,
        num_results=max_search_results,
        download_folder=pdf_download_folder
    )