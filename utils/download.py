#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
下载工具模块
提供单线程和多线程下载功能
"""
import os
import zipfile
import tempfile
import shutil
import datetime
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx
from loguru import logger

try:
    from colorama import init, Fore, Style
    COLORAMA_AVAILABLE = True
except ImportError:
    COLORAMA_AVAILABLE = False


def download_chunk(url, start, end, chunk_id, progress_queue, temp_file_path, client=None):
    """下载文件的一个分片并直接写入文件
    
    Args:
        url: 下载URL
        start: 分片开始字节位置
        end: 分片结束字节位置
        chunk_id: 分片ID
        progress_queue: 进度报告队列
        temp_file_path: 临时文件路径
        client: HTTP客户端实例
    
    Returns:
        tuple: (chunk_id, bytes_written)
    """
    headers = {'Range': f'bytes={start}-{end}'}
    
    # 如果没有传入客户端，创建一个新的
    if client is None:
        client = httpx.Client(timeout=60.0)
        should_close = True
    else:
        should_close = False
    
    bytes_written = 0
    
    try:
        with client.stream("GET", url, headers=headers) as response:
            response.raise_for_status()
            
            # 打开文件并定位到正确位置
            with open(temp_file_path, 'r+b') as f:
                f.seek(start)
                
                for data in response.iter_bytes(chunk_size=8192):
                    f.write(data)
                    bytes_written += len(data)
                    # 实时报告进度
                    progress_queue.put(('progress', chunk_id, len(data)))
        
        return chunk_id, bytes_written
        
    except Exception as e:
        progress_queue.put(('error', chunk_id, str(e)))
        raise
    finally:
        if should_close:
            client.close()


def download_with_multithread(download_url, target_dir, extract_zip: bool = True, num_threads: int = 4):
    """使用多线程分片下载文件并解压缩到目标目录
    
    Args:
        download_url: 下载URL
        target_dir: 目标目录
        extract_zip: 是否解压ZIP文件
        num_threads: 线程数
    
    Returns:
        bool: 下载是否成功
    """
    # 配置下载信息
    extract_file_name = download_url.split("/")[-1]
    target_dir = Path(os.getcwd()) / target_dir

    # 先清空目标文件夹
    if target_dir.exists() and target_dir.is_dir():
        shutil.rmtree(target_dir)

    logger.info("{}开始多线程下载依赖文件...", extract_file_name)
    logger.info(f"下载地址: {download_url}")
    logger.info(f"目标目录: {target_dir}")
    logger.info(f"线程数: {num_threads}")

    # 创建下载缓存目录
    cache_dir = Path(os.getcwd()) / ".download_cache"
    cache_dir.mkdir(exist_ok=True)
    
    # 检查缓存文件是否存在
    cached_file = cache_dir / extract_file_name
    temp_path = cache_dir / f"{extract_file_name}.tmp"
    
    # 如果缓存文件存在，尝试使用缓存
    if cached_file.exists():
        logger.info(f"发现缓存文件: {cached_file}")
        try:
            # 验证缓存文件是否完整
            if extract_zip:
                # 尝试打开ZIP文件验证完整性
                with zipfile.ZipFile(cached_file, "r") as zip_ref:
                    zip_ref.testzip()  # 验证ZIP文件完整性
                logger.success("缓存文件验证通过，使用缓存文件")
                
                # 直接解压缓存文件
                if extract_zip:
                    _extract_zip_file(cached_file, target_dir, extract_file_name)
                logger.success("从缓存安装完成!")
                return True
        except (zipfile.BadZipFile, zipfile.LargeZipFile) as e:
            logger.warning(f"缓存文件损坏，将重新下载: {e}")
            # 删除损坏的缓存文件
            try:
                os.unlink(cached_file)
            except:
                pass
        except Exception as e:
            logger.warning(f"缓存文件验证失败，将重新下载: {e}")

    try:
        # 创建HTTP客户端
        client = httpx.Client(timeout=60.0)
        
        # 首先获取文件大小
        response = client.head(download_url)
        response.raise_for_status()
        total_size = int(response.headers.get("content-length", 0))
        
        # 检查服务器是否支持分片下载
        accept_ranges = response.headers.get("accept-ranges", "").lower()
        if accept_ranges != "bytes" or total_size == 0:
            logger.warning("服务器不支持分片下载，使用单线程下载")
            client.close()
            return download_single_thread(download_url, target_dir, extract_zip)

        logger.info(f"文件大小: {total_size:,} bytes")

        # 创建临时文件并预分配空间
        with open(temp_path, 'wb') as temp_file:
            # 预分配文件空间
            temp_file.seek(total_size - 1)
            temp_file.write(b'\0')
            temp_file.flush()

        logger.info(f"已创建临时文件: {temp_path}")
        logger.info(f"预分配文件空间: {total_size:,} bytes")

        # 计算每个分片的大小
        chunk_size = total_size // num_threads
        chunks = []
        
        for i in range(num_threads):
            start = i * chunk_size
            if i == num_threads - 1:  # 最后一个分片包含剩余所有字节
                end = total_size - 1
            else:
                end = start + chunk_size - 1
            chunks.append((start, end, i))

        logger.info(f"分片信息: {len(chunks)} 个分片，每片约 {chunk_size:,} bytes")

        # 进度跟踪 - 移除内存中的分片缓存
        total_downloaded = 0
        completed_chunks = set()
        progress_queue = queue.Queue()
        download_lock = threading.Lock()

        # 初始化colorama（如果可用）
        if COLORAMA_AVAILABLE:
            init(autoreset=True)

        # 进度显示函数
        def update_progress():
            nonlocal total_downloaded
            last_update_time = 0
            update_interval = 0.1  # 每100ms更新一次显示
            
            while True:
                try:
                    item = progress_queue.get(timeout=0.5)
                    if item[0] == 'progress':
                        _, chunk_id, size = item
                        with download_lock:
                            total_downloaded += size
                            progress = (total_downloaded / total_size) * 100
                            
                            # 控制更新频率
                            current_time_ms = datetime.datetime.now().timestamp()
                            if current_time_ms - last_update_time >= update_interval:
                                last_update_time = current_time_ms
                                
                                # 实时显示进度
                                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                                
                                if COLORAMA_AVAILABLE:
                                    if progress < 30:
                                        progress_color = Fore.RED
                                    elif progress < 70:
                                        progress_color = Fore.YELLOW
                                    else:
                                        progress_color = Fore.GREEN
                                    
                                    print(
                                        f"\r{Fore.GREEN}{current_time}{Style.RESET_ALL} | "
                                        f"{Fore.CYAN}INFO    {Style.RESET_ALL} | "
                                        f"{Fore.MAGENTA}多线程下载{Style.RESET_ALL} | "
                                        f"{Fore.WHITE}{extract_file_name}{Style.RESET_ALL}: "
                                        f"{progress_color}{progress:.1f}%{Style.RESET_ALL} "
                                        f"({Fore.BLUE}{total_downloaded:,}{Style.RESET_ALL}/"
                                        f"{Fore.BLUE}{total_size:,}{Style.RESET_ALL} bytes) "
                                        f"[{Fore.YELLOW}{num_threads}线程{Style.RESET_ALL}]",
                                        end="",
                                        flush=True,
                                    )
                                else:
                                    print(
                                        f"\r{current_time} | INFO     | 多线程下载 | {extract_file_name}: {progress:.1f}% ({total_downloaded:,}/{total_size:,} bytes) [{num_threads}线程]",
                                        end="",
                                        flush=True,
                                    )
                    elif item[0] == 'done':
                        break
                    elif item[0] == 'error':
                        _, chunk_id, error = item
                        logger.error(f"分片 {chunk_id} 下载失败: {error}")
                except queue.Empty:
                    # 超时时也显示当前进度
                    with download_lock:
                        if total_downloaded > 0:
                            progress = (total_downloaded / total_size) * 100
                            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                            
                            if COLORAMA_AVAILABLE:
                                if progress < 30:
                                    progress_color = Fore.RED
                                elif progress < 70:
                                    progress_color = Fore.YELLOW
                                else:
                                    progress_color = Fore.GREEN
                                
                                print(
                                    f"\r{Fore.GREEN}{current_time}{Style.RESET_ALL} | "
                                    f"{Fore.CYAN}INFO    {Style.RESET_ALL} | "
                                    f"{Fore.MAGENTA}多线程下载{Style.RESET_ALL} | "
                                    f"{Fore.WHITE}{extract_file_name}{Style.RESET_ALL}: "
                                    f"{progress_color}{progress:.1f}%{Style.RESET_ALL} "
                                    f"({Fore.BLUE}{total_downloaded:,}{Style.RESET_ALL}/"
                                    f"{Fore.BLUE}{total_size:,}{Style.RESET_ALL} bytes) "
                                    f"[{Fore.YELLOW}{num_threads}线程{Style.RESET_ALL}]",
                                    end="",
                                    flush=True,
                                )
                            else:
                                print(
                                    f"\r{current_time} | INFO     | 多线程下载 | {extract_file_name}: {progress:.1f}% ({total_downloaded:,}/{total_size:,} bytes) [{num_threads}线程]",
                                    end="",
                                    flush=True,
                                )
                    continue

        # 启动进度显示线程
        progress_thread = threading.Thread(target=update_progress, daemon=True)
        progress_thread.start()
        
        # 初始进度显示
        logger.info("开始多线程下载...")

        # 使用线程池下载分片
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            # 提交下载任务
            future_to_chunk = {
                executor.submit(download_chunk, download_url, start, end, chunk_id, progress_queue, temp_path): (start, end, chunk_id)
                for start, end, chunk_id in chunks
            }

            # 收集结果
            for future in as_completed(future_to_chunk):
                start, end, chunk_id = future_to_chunk[future]
                try:
                    chunk_id, bytes_written = future.result()
                    completed_chunks.add(chunk_id)
                    # logger.debug(f"分片 {chunk_id} 下载完成: {bytes_written:,} bytes")
                except Exception as e:
                    logger.error(f"分片 {chunk_id} 下载失败: {e}")
                    raise

        # 关闭HTTP客户端
        client.close()

        # 停止进度显示
        progress_queue.put(('done',))
        progress_thread.join(timeout=1)
        print("")  # 换行

        # 验证所有分片都已完成
        logger.info("验证分片完整性...")
        if len(completed_chunks) != num_threads:
            missing_chunks = set(range(num_threads)) - completed_chunks
            raise RuntimeError(f"分片下载不完整，缺失分片: {missing_chunks}")

        # 验证文件大小
        actual_size = os.path.getsize(temp_path)
        if actual_size != total_size:
            raise RuntimeError(f"文件大小不匹配: 期望 {total_size:,} bytes, 实际 {actual_size:,} bytes")

        logger.success(f"{extract_file_name} 多线程下载完成")

        # 将临时文件移动到缓存位置
        shutil.move(str(temp_path), str(cached_file))
        logger.info(f"文件已缓存到: {cached_file}")

        # 解压缩文件
        if extract_zip:
            _extract_zip_file(cached_file, target_dir, extract_file_name)

        logger.success("多线程下载安装完成!")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP错误: {e.response.status_code} {e.response.reason_phrase}")
        return False
    except httpx.TimeoutException:
        logger.error("下载超时")
        return False
    except httpx.RequestError as e:
        logger.error(f"网络请求失败: {e}")
        return False
    except zipfile.BadZipFile as e:
        logger.error(f"解压失败，文件损坏: {e}")
        return False
    except Exception as e:
        logger.error(f"多线程下载过程中发生错误: {e}")
        return False
    finally:
        # 确保关闭HTTP客户端
        if "client" in locals():
            try:
                client.close()
            except:
                pass
        # 确保清理临时文件
        if "temp_path" in locals() and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

    return True


def download_single_thread(download_url, target_dir, extract_zip: bool = True):
    """单线程下载文件并解压缩到目标目录
    
    Args:
        download_url: 下载URL
        target_dir: 目标目录
        extract_zip: 是否解压ZIP文件
    
    Returns:
        bool: 下载是否成功
    """
    # 配置下载信息
    extract_file_name = download_url.split("/")[-1]
    target_dir = Path(os.getcwd()) / target_dir

    # 先清空目标文件夹下所有
    if target_dir.exists() and target_dir.is_dir():
        shutil.rmtree(target_dir)

    logger.info("{}开始下载依赖文件...", extract_file_name)
    logger.info(f"下载地址: {download_url}")
    logger.info(f"目标目录: {target_dir}")

    # 创建下载缓存目录
    cache_dir = Path(os.getcwd()) / ".download_cache"
    cache_dir.mkdir(exist_ok=True)
    
    # 检查缓存文件是否存在
    cached_file = cache_dir / extract_file_name
    temp_path = cache_dir / f"{extract_file_name}.tmp"
    
    # 如果缓存文件存在，尝试使用缓存
    if cached_file.exists():
        logger.info(f"发现缓存文件: {cached_file}")
        try:
            # 验证缓存文件是否完整
            if extract_zip:
                # 尝试打开ZIP文件验证完整性
                with zipfile.ZipFile(cached_file, "r") as zip_ref:
                    zip_ref.testzip()  # 验证ZIP文件完整性
                logger.success("缓存文件验证通过，使用缓存文件")
                
                # 直接解压缓存文件
                if extract_zip:
                    _extract_zip_file(cached_file, target_dir, extract_file_name)
                logger.success("从缓存安装完成!")
                return True
        except (zipfile.BadZipFile, zipfile.LargeZipFile) as e:
            logger.warning(f"缓存文件损坏，将重新下载: {e}")
            # 删除损坏的缓存文件
            try:
                os.unlink(cached_file)
            except:
                pass
        except Exception as e:
            logger.warning(f"缓存文件验证失败，将重新下载: {e}")

    try:
        # 创建下载缓存目录
        cache_dir = Path(os.getcwd()) / ".download_cache"
        cache_dir.mkdir(exist_ok=True)
        
        # 创建临时文件
        temp_path = cache_dir / f"{extract_file_name}.tmp"
        
        with open(temp_path, 'wb') as temp_file:
            # 使用 httpx 下载文件
            logger.info("正在下载文件...")

            with httpx.stream("GET", download_url, timeout=60.0) as response:
                response.raise_for_status()

                total_size = int(response.headers.get("content-length", 0))
                downloaded_size = 0
                
                # 初始化colorama（如果可用）
                if COLORAMA_AVAILABLE:
                    init(autoreset=True)

                for chunk in response.iter_bytes(chunk_size=8192):
                    temp_file.write(chunk)
                    downloaded_size += len(chunk)

                    if total_size > 0:
                        progress = (downloaded_size / total_size) * 100
                        # 实时时间戳，格式类似loguru
                        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        if COLORAMA_AVAILABLE:
                            # 带颜色的版本
                            # 根据进度调整颜色
                            if progress < 30:
                                progress_color = Fore.RED
                            elif progress < 70:
                                progress_color = Fore.YELLOW
                            else:
                                progress_color = Fore.GREEN
                            
                            print(
                                f"\r{Fore.GREEN}{current_time}{Style.RESET_ALL} | "
                                f"{Fore.CYAN}INFO    {Style.RESET_ALL} | "
                                f"{Fore.MAGENTA}下载进度{Style.RESET_ALL} | "
                                f"{Fore.WHITE}{extract_file_name}{Style.RESET_ALL}: "
                                f"{progress_color}{progress:.1f}%{Style.RESET_ALL} "
                                f"({Fore.BLUE}{downloaded_size:,}{Style.RESET_ALL}/"
                                f"{Fore.BLUE}{total_size:,}{Style.RESET_ALL} bytes)",
                                end="",
                                flush=True,
                            )
                        else:
                            # 无颜色的版本
                            print(
                                f"\r{current_time} | INFO     | 下载进度 | {extract_file_name}: {progress:.1f}% ({downloaded_size:,}/{total_size:,} bytes)",
                                end="",
                                flush=True,
                            )
        
        print("")  # 换行
        logger.success(f"{extract_file_name} 文件下载完成")

        # 将临时文件移动到缓存位置
        shutil.move(str(temp_path), str(cached_file))
        logger.info(f"文件已缓存到: {cached_file}")

        # 解压缩文件
        if extract_zip:
            _extract_zip_file(cached_file, target_dir, extract_file_name)

        logger.success("安装完成!")

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP错误: {e.response.status_code} {e.response.reason_phrase}")
        return False
    except httpx.TimeoutException:
        logger.error("下载超时")
        return False
    except httpx.RequestError as e:
        logger.error(f"网络请求失败: {e}")
        return False
    except zipfile.BadZipFile as e:
        logger.error(f"解压失败，文件损坏: {e}")
        return False
    except Exception as e:
        logger.error(f"安装过程中发生错误: {e}")
        return False
    finally:
        # 确保清理临时文件
        if "temp_path" in locals() and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except:
                pass

    return True


def _extract_zip_file(zip_path, target_dir, file_name):
    """解压ZIP文件的辅助函数
    
    Args:
        zip_path: ZIP文件路径
        target_dir: 目标目录
        file_name: 文件名（用于日志）
    """
    logger.info("正在解压缩文件...")
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        # 获取压缩包内的文件列表
        file_list = zip_ref.namelist()
        logger.info(f"压缩包包含 {len(file_list)} 个文件")

        # 解压到目标目录
        zip_ref.extractall(target_dir)
        logger.success(f"文件已解压到: {target_dir}")

        # 显示解压的文件
        for file_name in file_list[:10]:  # 只显示前10个文件
            logger.info(f"  - {file_name}")
        if len(file_list) > 10:
            logger.info(f"  ... 还有 {len(file_list) - 10} 个文件")


def clean_download_cache():
    """清理下载缓存目录
    
    Returns:
        bool: 清理是否成功
    """
    try:
        cache_dir = Path(os.getcwd()) / ".download_cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            logger.success(f"已清理下载缓存目录: {cache_dir}")
            return True
        else:
            logger.info("下载缓存目录不存在，无需清理")
            return True
    except Exception as e:
        logger.error(f"清理下载缓存失败: {e}")
        return False


def get_cache_size():
    """获取下载缓存目录的大小
    
    Returns:
        int: 缓存大小（字节）
    """
    try:
        cache_dir = Path(os.getcwd()) / ".download_cache"
        if not cache_dir.exists():
            return 0
        
        total_size = 0
        for file_path in cache_dir.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        
        return total_size
    except Exception as e:
        logger.error(f"获取缓存大小失败: {e}")
        return 0


def list_cache_files():
    """列出缓存目录中的文件
    
    Returns:
        list: 缓存文件列表
    """
    try:
        cache_dir = Path(os.getcwd()) / ".download_cache"
        if not cache_dir.exists():
            return []
        
        cache_files = []
        for file_path in cache_dir.iterdir():
            if file_path.is_file() and not file_path.name.endswith('.tmp'):
                file_info = {
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'modified': datetime.datetime.fromtimestamp(file_path.stat().st_mtime),
                    'path': str(file_path)
                }
                cache_files.append(file_info)
        
        return sorted(cache_files, key=lambda x: x['modified'], reverse=True)
    except Exception as e:
        logger.error(f"列出缓存文件失败: {e}")
        return []


def show_cache_info():
    """显示缓存信息"""
    cache_files = list_cache_files()
    total_size = get_cache_size()
    
    logger.info("=== 下载缓存信息 ===")
    logger.info(f"缓存目录: {Path(os.getcwd()) / '.download_cache'}")
    logger.info(f"总大小: {total_size:,} bytes ({total_size / 1024 / 1024:.2f} MB)")
    logger.info(f"文件数量: {len(cache_files)}")
    
    if cache_files:
        logger.info("缓存文件列表:")
        for file_info in cache_files:
            size_mb = file_info['size'] / 1024 / 1024
            logger.info(f"  - {file_info['name']} ({size_mb:.2f} MB, {file_info['modified'].strftime('%Y-%m-%d %H:%M:%S')})")
    else:
        logger.info("暂无缓存文件")
    logger.info("===================")


# 向后兼容的别名
install_dependencies_with_multithread = download_with_multithread
install_dependencies = download_single_thread
