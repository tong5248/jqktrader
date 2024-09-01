import re

import requests
from PIL import Image

from jqktrader import exceptions
import pytesseract

'''注释部分是原文件，20240901修改了def captcha_recognize(img_path)，修改后测试可用
def captcha_recognize(img_path):
    """使用tesseract识别验证码"""
    import pytesseract  # 导入tesseract库

    # 打开图片并转换为灰度图像
    im = Image.open(img_path).convert("L")
    
    # 1. 对图像进行阈值处理
    threshold = 200  # 定义阈值
    table = []  # 初始化映射表
    for i in range(256):
        if i < threshold:
            table.append(0)  # 小于阈值的像素设置为0（黑色）
        else:
            table.append(1)  # 大于阈值的像素设置为1（白色）

    # 应用阈值处理
    out = im.point(table, "1")
    
    # 2. 使用tesseract进行识别
    num = pytesseract.image_to_string(out)
    return num  # 返回识别结果
'''
def captcha_recognize(img_path):
    """ 使用 pytesseract 识别验证码 """
    captcha_image = Image.open(img_path)
    captcha_text = pytesseract.image_to_string(captcha_image, config='--psm 8 outputbase digits')
    return captcha_text.strip()


def recognize_verify_code(image_path, broker="ht"):
    """识别验证码，返回识别后的字符串，使用 tesseract 实现
    :param image_path: 图片路径
    :param broker: 券商 ['ht', 'yjb', 'gf', 'yh']
    :return recognized: verify code string"""

    if broker == "gf":
        return detect_gf_result(image_path)
    if broker in ["yh_client", "gj_client"]:
        return detect_yh_client_result(image_path)
    # 调用 tesseract 识别
    return default_verify_code_detect(image_path)


def detect_yh_client_result(image_path):
    """封装了tesseract的识别，部署在阿里云上，
    服务端源码地址为： https://github.com/shidenggui/yh_verify_code_docker"""
    api = "http://yh.ez.shidenggui.com:5000/yh_client"
    with open(image_path, "rb") as f:
        rep = requests.post(api, files={"image": f})
    if rep.status_code != 201:
        error = rep.json()["message"]
        raise exceptions.TradeError("request {} error: {}".format(api, error))
    return rep.json()["result"]


def input_verify_code_manual(image_path):
    from PIL import Image

    image = Image.open(image_path)
    image.show()
    code = input(
        "image path: {}, input verify code answer:".format(image_path)
    )
    return code


def default_verify_code_detect(image_path):
    from PIL import Image

    img = Image.open(image_path)
    return invoke_tesseract_to_recognize(img)


def detect_gf_result(image_path):
    from PIL import ImageFilter, Image

    img = Image.open(image_path)
    if hasattr(img, "width"):
        width, height = img.width, img.height
    else:
        width, height = img.size
    for x in range(width):
        for y in range(height):
            if img.getpixel((x, y)) < (100, 100, 100):
                img.putpixel((x, y), (256, 256, 256))
    gray = img.convert("L")
    two = gray.point(lambda p: 0 if 68 < p < 90 else 256)
    min_res = two.filter(ImageFilter.MinFilter)
    med_res = min_res.filter(ImageFilter.MedianFilter)
    for _ in range(2):
        med_res = med_res.filter(ImageFilter.MedianFilter)
    return invoke_tesseract_to_recognize(med_res)


def invoke_tesseract_to_recognize(img):
    import pytesseract

    try:
        res = pytesseract.image_to_string(img)
    except FileNotFoundError:
        raise Exception(
            "tesseract 未安装，请至 https://github.com/tesseract-ocr/tesseract/wiki 查看安装教程"
        )
    valid_chars = re.findall("[0-9a-z]", res, re.IGNORECASE)
    return "".join(valid_chars)
