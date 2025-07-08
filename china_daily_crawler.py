#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""
@Project    ：ChinaDailyCrawler
@File       ：china_daily_crawler.py
@Author     ：IronmanJay
@Date       ：2025/7/8 23:38
@Describe   ：基于selenium的ChinaDaily新闻信息爬取
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.edge.service import Service as EdgeService
from selenium.webdriver.edge.options import Options as EdgeOptions
import csv
import time
import re
import random


def get_news_links(driver):
    """
    从搜索结果页面获取所有新闻链接
    :param driver: 浏览器驱动
    :return: 所有新闻链接
    """
    print("获取新闻链接...")
    news_links = []

    # 等待新闻列表加载
    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".lft_art .art_detail"))
        )
    except:
        print("等待新闻列表超时")
        return []

    # 找到所有新闻条目
    news_items = driver.find_elements(By.CSS_SELECTOR, ".lft_art .art_detail")
    print(f"找到 {len(news_items)} 个新闻条目")

    # 提取每个新闻的链接
    for item in news_items:
        try:
            # 找到标题链接
            title_link = item.find_element(By.CSS_SELECTOR, "h4 a")
            href = title_link.get_attribute("href")
            title = title_link.text.strip()

            # 提取来源和时间
            source_time = item.find_element(By.CSS_SELECTOR, "b").text.strip()

            # 添加到结果列表
            news_links.append({
                "title": title,
                "url": href,
                "source_time": source_time
            })
        except Exception as e:
            print(f"提取新闻链接时出错: {str(e)}")

    return news_links


def get_total_pages(driver):
    """
    获取总页数
    :param driver: 浏览器驱动
    :return: 总页数
    """
    try:
        # 方法1：从结果计数中提取总结果数
        try:
            result_count = driver.find_element(By.CSS_SELECTOR, ".results span").text
            print(f"结果计数文本: {result_count}")

            if "of" in result_count:
                parts = result_count.split('of')
                if len(parts) > 1:
                    total_results = parts[1].strip().split()[0]
                    # 计算总页数（假设每页10条结果）
                    return (int(total_results) + 9) // 10
        except:
            pass

        # 方法2：从分页控件中提取总页数
        try:
            # 找到分页信息元素
            page_info = driver.find_element(By.CSS_SELECTOR, ".page rt")
            page_text = page_info.text.strip()
            print(f"分页控件文本: {page_text}")

            # 提取总页数 (格式: "Page:1 2 3 4 5 NEXT >>")
            if 'NEXT' in page_text:
                # 计算按钮数量
                buttons = page_info.find_elements(By.TAG_NAME, "a")
                # 最后一个按钮是NEXT，前面的按钮是页码
                last_page = int(buttons[-2].text) if buttons[-2].text.isdigit() else len(buttons) - 1
                return last_page
        except:
            pass

        # 方法3：从分页信息中直接提取
        try:
            page_info = driver.find_element(By.CSS_SELECTOR, ".selectpage .pageno a")
            page_text = page_info.text.strip()
            print(f"分页信息文本: {page_text}")

            # 提取总页数 (格式: "1/6")
            if '/' in page_text:
                _, total_pages = page_text.split('/')
                return int(total_pages)
        except:
            pass

    except Exception as e:
        print(f"获取总页数时出错: {str(e)}")

    # 默认返回1页
    print("无法确定总页数，默认返回1页")
    return 1


def go_to_next_page(driver, current_page):
    """
    导航到下一页
    :param driver: 浏览器驱动
    :param current_page: 当前页
    :return: 是否成功导航到下一页
    """
    try:
        print(f"尝试导航到第 {current_page + 1} 页...")

        # 查找下一页按钮
        next_button = driver.find_element(By.XPATH, '//a[contains(., "NEXT")]')

        # 点击下一页按钮
        next_button.click()

        # 等待页面加载完成
        WebDriverWait(driver, 15).until(
            lambda d: d.find_element(By.CSS_SELECTOR, ".results span").text != ""
        )

        # 确保新闻列表已加载
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".lft_art .art_detail"))
        )

        print(f"成功导航到第 {current_page + 1} 页")
        return True
    except Exception as e:
        print(f"导航到下一页时出错: {str(e)}")
        screenshot_name = f"page_error_{time.strftime('%Y%m%d_%H%M%S')}.png"
        driver.save_screenshot(screenshot_name)
        print(f"已保存页面截图: {screenshot_name}")
        return False


def extract_news_content(driver, url):
    """
    从新闻详情页提取标题和内容
    :param driver: 浏览器驱动
    :param url: 目标url
    :return: 提取结果
    """
    print(f"访问新闻页面: {url}")

    # 在新标签页打开新闻
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[1])
    driver.get(url)

    content = ""
    title = ""

    try:
        # 尝试多种标题选择器
        title_selectors = [
            ".dabiaoti",        # 主选择器
            "Artical_Title",    # 备用选择器1
            "h1",               # 备用选择器2
            ".title",           # 备用选择器3
            ".headline"         # 备用选择器4
        ]

        # 等待标题加载
        WebDriverWait(driver, 15).until(
            lambda d: any(d.find_elements(By.CSS_SELECTOR, s) for s in title_selectors)
        )

        # 提取标题
        for selector in title_selectors:
            try:
                title_element = driver.find_element(By.CSS_SELECTOR, selector)
                title = title_element.text.strip()
                if title:
                    print(f"使用选择器 '{selector}' 找到标题")
                    break
            except:
                continue

        if not title:
            print("警告: 未找到标题")

        # 尝试多种内容区域选择器
        content_selectors = [
            "#zw",                  # 主选择器
            "#Content",             # 备用选择器1
            "Artical_Content",      # 备用选择器2
            ".article",             # 备用选择器3
            ".article-content",     # 备用选择器4
            ".article-body"         # 备用选择器5
        ]

        content_div = None
        for selector in content_selectors:
            try:
                content_div = driver.find_element(By.CSS_SELECTOR, selector)
                print(f"使用选择器 '{selector}' 找到内容区域")
                break
            except:
                continue

        if not content_div:
            raise Exception("无法定位内容区域")

        # 提取所有段落
        paragraphs = content_div.find_elements(By.XPATH, ".//p[normalize-space()]")
        for p in paragraphs:
            text = p.text.strip()
            # 过滤免责声明等非正文内容
            if not text or "免责声明" in text or "责任编辑" in text:
                continue
            content += text + "\n\n"

        # 如果没有段落，直接获取整个文本
        if not content:
            print("警告: 通过段落未提取到内容，尝试获取整个文本")
            content = content_div.text.strip()

        # 清理内容
        if content:
            content = re.sub(r'\s*免责声明：.*$', '', content, flags=re.DOTALL)
            content = re.sub(r'\s*【责任编辑.*$', '', content, flags=re.DOTALL)
            content = re.sub(r'\s+', ' ', content).strip()
            print(f"成功提取内容，长度: {len(content)} 字符")

    except Exception as e:
        print(f"提取内容时出错: {str(e)}")
        screenshot_name = f"error_{time.strftime('%Y%m%d_%H%M%S')}.png"
        driver.save_screenshot(screenshot_name)
        print(f"已保存页面截图: {screenshot_name}")

    finally:
        # 关闭当前标签页并切换回主标签页
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        # 随机延迟
        time.sleep(random.uniform(1.0, 2.0))

    return title, content


def save_to_csv(data, filename):
    """
    保存数据到CSV文件
    :param data: 爬取到的数据
    :param filename: 保存数据的目标文件名
    :return: None
    """
    with open(filename, 'w', newline='', encoding='utf-8-sig') as csvfile:
        fieldnames = ['title', 'url', 'source_time', 'content']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

        writer.writeheader()
        for row in data:
            writer.writerow({
                'title': row['title'],
                'url': row['url'],
                'source_time': row['source_time'],
                'content': row['content']
            })

    print(f"CSV文件已保存: {filename}")


def main():
    # 配置Edge选项
    edge_options = EdgeOptions()
    edge_options.add_argument("--disable-gpu")
    edge_options.add_argument("--no-sandbox")
    edge_options.add_argument("--disable-dev-shm-usage")
    edge_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36 Edg/125.0.0.0")

    # 初始化Edge浏览器
    print("启动Microsoft Edge浏览器...")
    service = EdgeService()
    driver = webdriver.Edge(service=service, options=edge_options)
    driver.set_window_size(1920, 1080)

    # 目标URL
    target_url = "https://newssearch.chinadaily.com.cn/cn/search?cond=%7B%22publishedDateFrom%22%3A%222024-11-11%22%2C%22publishedDateTo%22%3A%222024-11-22%22%2C%22fullMust%22%3A%22%E6%B0%94%E5%80%99%22%2C%22fullAny%22%3A%22cop29%22%2C%22sort%22%3A%22dp%22%2C%22duplication%22%3A%22off%22%7D&language=cn"

    print(f"访问目标页面: {target_url}")
    driver.get(target_url)

    # 等待页面加载完成
    WebDriverWait(driver, 15).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".lft_art .art_detail"))
    )

    # 等待分页信息加载
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".page, .results"))
    )

    # 获取总页数
    total_pages = get_total_pages(driver)
    print(f"检测到总页数: {total_pages}")

    # 收集所有新闻链接
    all_news_links = []

    # 处理当前页
    for page in range(total_pages):
        print(f"\n处理第 {page + 1}/{total_pages} 页")

        # 获取当前页的新闻链接
        news_links = get_news_links(driver)

        if not news_links:
            print(f"第 {page + 1} 页未找到新闻链接")
        else:
            all_news_links.extend(news_links)
            print(f"成功收集 {len(news_links)} 条新闻链接")

        # 更新页数显示
        current_page = page + 1

        # 如果不是最后一页，导航到下一页
        if current_page < total_pages:
            if not go_to_next_page(driver, current_page):
                print("无法导航到下一页，停止翻页")
                break

            # 添加页面间延迟
            delay = random.uniform(3.0, 5.0)
            print(f"等待 {delay:.1f} 秒后继续...")
            time.sleep(delay)

    print(f"\n总共收集到 {len(all_news_links)} 条新闻链接")

    if not all_news_links:
        print("未找到任何新闻链接，退出程序")
        driver.quit()
        return

    # 提取每个新闻的内容
    news_data = []
    for i, link_info in enumerate(all_news_links):
        print(f"\n处理新闻 {i + 1}/{len(all_news_links)}: {link_info['title']}")

        # 提取新闻内容
        title, content = extract_news_content(driver, link_info['url'])

        # 如果成功提取到内容
        if content:
            news_data.append({
                "title": title or link_info['title'],
                "url": link_info['url'],
                "source_time": link_info['source_time'],
                "content": content
            })
        else:
            print("未提取到内容")

        # 避免请求过快，添加随机延迟
        delay = random.uniform(3.0, 6.0)
        print(f"等待 {delay:.1f} 秒后继续...")
        time.sleep(delay)

    # 关闭浏览器
    driver.quit()
    print("浏览器已关闭")

    # 保存结果
    if news_data:
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        filename = f'china_daily_climate_news_{timestamp}.csv'
        save_to_csv(news_data, filename)
        print(f"\n成功提取 {len(news_data)} 条新闻数据，已保存到 {filename}")
    else:
        print("未提取到任何新闻数据")


if __name__ == "__main__":
    main()
