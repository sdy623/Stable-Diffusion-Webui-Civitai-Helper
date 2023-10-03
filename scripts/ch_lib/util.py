# -*- coding: UTF-8 -*-
import os
import io
import hashlib
import requests
import shutil


version = "1.8.2"

def_headers = {'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'}


proxies = None


from PIL import Image, ImageDraw, ImageFont, ImageFilter
import json
import smartcrop
import re


def get_font_size(std_font_size, text, max_width, font_file):
    # 设置一个初始的字体大小
    std_font_size = 30
    font = ImageFont.truetype(font_file, std_font_size)

    # 检查文本的宽度是否超过最大宽度
    while font.getsize(text)[0] > max_width:
        font_size -= 1  # 减小字体大小
        font = ImageFont.truetype(font_file, font_size)

    return font

def strip_text(text, font, max_width):
    if (font.getsize(text)[0] > max_width):
        if len(extract_chinese(text)) > 0:
            text = extract_chinese(text)
        else:
            text = text[:11]

    return text

def extract_chinese(text):
    chinese_text = re.findall(r'[\u4e00-\u9fa5]+|\d+$', text)
    return ''.join(chinese_text)

def extract_main_element(image):
    if image.mode == 'RGBA':
        image = image.convert('RGB')
    outer_ratio= 512 / 405
    width, height = image.size
    cropper = smartcrop.SmartCrop()
    corn_info  = cropper.crop(image, 512, 512)

    inner_left = corn_info['top_crop']['x']
    inner_top = corn_info['top_crop']['y']
    inner_right = inner_left + corn_info['top_crop']['width']
    inner_bottom = inner_top + corn_info['top_crop']['height']

    # 裁剪图片
    image = image.crop((inner_left, inner_top, inner_right, inner_bottom))
    
    return image  # 返回裁剪后的图片

def draw_rounded_rectangle(draw, xy, corner_radius, fill=None, outline=None):
    x1, y1, x2, y2 = xy

    # 上左边线
    draw.line([(x1, y1 + corner_radius), (x1, y2 - corner_radius)], fill=fill)
    # 下左边线
    draw.line([(x1, y2), (x2, y2)], fill=fill)
    # 上右边线
    draw.line([(x2, y1 + corner_radius), (x2, y2 - corner_radius)], fill=fill)
    # 上边线
    draw.line([(x1, y1), (x2, y1)], fill=fill)
    
    # 右上圆弧
    draw.pieslice([x2 - corner_radius * 2, y1, x2, y1 + corner_radius * 2], 0, 90, fill=fill)
    # 右下圆弧
    draw.pieslice([x2 - corner_radius * 2, y2 - corner_radius * 2, x2, y2], 270, 360, fill=fill)

def make_sqindex(rawimg, extra_param):
    # 从JSON文件中读取信息

    model_name = extra_param['model_name']
    author_name = extra_param['author_name']
    model_type = extra_param['model_type']

    # 读取并处理模型的预览图
    image = Image.open(rawimg)
    image = extract_main_element(image)
    image = image.resize((512, 512), Image.Resampling.LANCZOS)

    supersample_factor = 4
    supersample_size = (image.width * supersample_factor, image.height * supersample_factor)

    # 创建一个蒙版
    mask = Image.new("L", supersample_size, 255)  # 使用白色初始化蒙版
    mask_draw = ImageDraw.Draw(mask)
    rect_x, rect_y, rect_width, rect_height = 48 * supersample_factor, 47 * supersample_factor, 419 * supersample_factor, 311 * supersample_factor
    mask_draw.rounded_rectangle(
        [(rect_x, rect_y), (rect_x+rect_width, rect_y+rect_height)],
        radius=45 * supersample_factor,
        fill=0  # 使用黑色填充矩形
    )

    # 将蒙版缩小回原始大小
    mask = mask.resize((512, 512), Image.Resampling.LANCZOS)

    # 应用蒙版
    darken_image = Image.eval(image, lambda px: px*1/7)
    image.paste(darken_image, mask=mask)

    draw = ImageDraw.Draw(image)

    width, height = image.size
    # 色带的坐标和尺寸
    band_x = 0  # 色带开始的x坐标
    band_y = height - 108  # 色带开始的y坐标
    band_width = 512  # 色带的宽度
    band_height = 108  # 色带的高度
    print(height)
    # 定义矩形参数
    weight_ex, height_ex2 = 312, 66
    large_image = Image.new("RGBA", (weight_ex * supersample_factor, height_ex2 * supersample_factor), (0, 0, 0, 0))
    large_draw = ImageDraw.Draw(large_image)
    rect_x, rect_y, rect_width, rect_height = 0 * supersample_factor, 0 * supersample_factor, 312 * supersample_factor, 66 * supersample_factor  # 高度随意设置
    corner_radius = 32 * supersample_factor
    fill_color = "#7848EA"

    # 绘制右上和右下倒角的矩形
    large_draw.rounded_rectangle(
    [(rect_x, rect_y), (rect_x+rect_width, rect_y+rect_height)],
    radius = corner_radius,  # 设置倒角半径
    fill = fill_color,  # 使用蓝色填充矩形
    corners = [0, 1, 1, 0]
    )
    
    p_image = large_image.resize((weight_ex, height_ex2), Image.ANTIALIAS)
    position = (0, 340)  # 这是粘贴的位置
    image.paste(p_image, position, p_image)  # 使用 image 作为 mask 以保持透明度

    # 绘制色带
    draw.rectangle([(band_x, band_y), (band_x + band_width, band_y + band_height)], fill='#383838')

    # 添加模型名和模型制作者名
    larger = 72
    smaller = 48

    model_name_font = ImageFont.truetype("AlibabaPuHuiTi-3-85-Bold.otf", larger)
    author_name_font = ImageFont.truetype("AlimamaShuHeiTi-Bold.otf", smaller)
    
    full_large_text = f'{strip_text(model_name, model_name_font, larger)}-{model_type}'
    draw.text((25, 405), full_large_text, font=model_name_font, fill="white")
    draw.text((25, 350), strip_text(author_name, author_name_font, larger), font=author_name_font ,fill="white")
    
    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='JPEG')

    img_byte_arr.seek(0)
    return img_byte_arr

# 用法示例

# print for debugging
def printD(msg):
    print(f"Civitai Helper: {msg}")


def read_chunks(file, size=io.DEFAULT_BUFFER_SIZE):
    """Yield pieces of data from a file-like object until EOF."""
    while True:
        chunk = file.read(size)
        if not chunk:
            break
        yield chunk

# Now, hashing use the same way as pip's source code.
def gen_file_sha256(filname):
    printD("Use Memory Optimized SHA256")
    blocksize=1 << 20
    h = hashlib.sha256()
    length = 0
    with open(os.path.realpath(filname), 'rb') as f:
        for block in read_chunks(f, size=blocksize):
            length += len(block)
            h.update(block)

    hash_value =  h.hexdigest()
    printD("sha256: " + hash_value)
    printD("length: " + str(length))
    return hash_value



# get preview image
def download_file(url, path, image_processor=None, extra_param=None):
    printD("Downloading file from: " + url)
    # get file
    r = requests.get(url, stream=True, headers=def_headers, proxies=proxies)
    if not r.ok:
        printD("Get error code: " + str(r.status_code))
        printD(r.text)
        return
    
    image_data = r.raw
    if image_processor:
        processed_image_data = image_processor(image_data, extra_param)
    else:
        processed_image_data = image_data
    
    # write to file
    with open(os.path.realpath(path), 'wb') as f:
        image_data.decode_content = True
        shutil.copyfileobj(processed_image_data, f)

    printD("File downloaded to: " + path)

# get subfolder list
def get_subfolders(folder:str) -> list:
    printD("Get subfolder for: " + folder)
    if not folder:
        printD("folder can not be None")
        return
    
    if not os.path.isdir(folder):
        printD("path is not a folder")
        return
    
    prefix_len = len(folder)
    subfolders = []
    for root, dirs, files in os.walk(folder, followlinks=True):
        for dir in dirs:
            full_dir_path = os.path.join(root, dir)
            # get subfolder path from it
            subfolder = full_dir_path[prefix_len:]
            subfolders.append(subfolder)

    return subfolders


# get relative path
def get_relative_path(item_path:str, parent_path:str) -> str:
    # printD("item_path:"+item_path)
    # printD("parent_path:"+parent_path)
    # item path must start with parent_path
    if not item_path:
        return ""
    if not parent_path:
        return ""
    if not item_path.startswith(parent_path):
        return item_path

    relative = item_path[len(parent_path):]
    if relative[:1] == "/" or relative[:1] == "\\":
        relative = relative[1:]

    # printD("relative:"+relative)
    return relative