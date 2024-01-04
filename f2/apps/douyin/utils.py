# path: f2/apps/douyin/utils.py

import f2
import re
import json
import time
import httpx
import qrcode
import random
import asyncio

from typing import Union
from pathlib import Path
from urllib.parse import quote, unquote

from f2.i18n.translator import _
from f2.log.logger import logger
from f2.utils.xbogus import XBogus as XB
from f2.utils.conf_manager import ConfigManager
from f2.utils.utils import (
    gen_random_str,
    get_timestamp,
    num_to_base36,
    extract_valid_urls,
)
from f2.exceptions.api_exceptions import (
    APIError,
    APIConnectionError,
    APIResponseError,
    APIUnavailableError,
    APIUnauthorizedError,
    APINotFoundError,
)


class TokenManager:
    dy_manager = ConfigManager(f2.APP_CONFIG_FILE_PATH)
    token_conf = dy_manager.get_config("douyin").get("msToken", None)
    ttwid_conf = dy_manager.get_config("douyin").get("ttwid", None)
    proxies_conf = dy_manager.get_config("douyin").get("proxies", None)
    proxies = {
        "http://": proxies_conf.get("http", None),
        "https://": proxies_conf.get("https", None),
    }

    @classmethod
    def gen_real_msToken(cls) -> str:
        """
        生成真实的msToken,当出现错误时返回虚假的值
        (Generate a real msToken and return a false value when an error occurs)
        """

        payload = json.dumps(
            {
                "magic": cls.token_conf["magic"],
                "version": cls.token_conf["version"],
                "dataType": cls.token_conf["dataType"],
                "strData": cls.token_conf["strData"],
                "tspFromClient": get_timestamp(),
            }
        )
        headers = {
            "User-Agent": cls.token_conf["User-Agent"],
            "Content-Type": "application/json",
        }

        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport, proxies=dict(cls.proxies)) as client:
            try:
                response = client.post(
                    cls.token_conf["url"], headers=headers, content=payload
                )

                if response.status_code == 401:
                    raise APIUnauthorizedError(_("由于某些错误, 无法获取msToken"))
                elif response.status_code == 404:
                    raise APINotFoundError(_("无法找到API端点"))

                msToken = str(httpx.Cookies(response.cookies).get("msToken"))

                return msToken

            except httpx.RequestError:
                # 捕获所有与 httpx 请求相关的异常情况 (Captures all httpx request-related exceptions)
                raise APIConnectionError(
                    _("连接端点失败: {0}").format(cls.token_conf["url"])
                )  # Failed to connect to endpoint

            except httpx.HTTPStatusError as e:
                # 捕获 httpx 的状态代码错误 (captures specific status code errors from httpx)
                raise APIResponseError(
                    f"HTTP Status Code {e.response.status_code}: {e.response.text}"
                )

            except APIError as e:
                e.display_error()
                # 返回虚假的msToken (Return a fake msToken)
                print(_("生成虚假的msToken"))
                return cls.gen_false_msToken()

    @classmethod
    def gen_false_msToken(cls) -> str:
        """生成随机msToken (Generate random msToken)"""
        return gen_random_str(126) + "=="

    @classmethod
    def gen_ttwid(cls) -> str:
        """
        生成请求必带的ttwid
        (Generate the essential ttwid for requests)
        """

        transport = httpx.HTTPTransport(retries=5)
        with httpx.Client(transport=transport) as client:
            try:
                response = client.post(
                    cls.ttwid_conf["url"], content=cls.ttwid_conf["data"]
                )

                if response.status_code == 401:
                    raise APIUnauthorizedError(
                        _("由于某些错误, 无法获取ttwid")
                    )  # (Unauthorized request,Unable to get ttwid)
                elif response.status_code == 404:
                    raise APINotFoundError(_("无法找到API端点"))

                ttwid = str(httpx.Cookies(response.cookies).get("ttwid"))
                return ttwid

            except httpx.RequestError:
                # 捕获所有与 httpx 请求相关的异常情况 (Captures all httpx request-related exceptions)
                raise APIConnectionError(_("连接端点失败: {0}").format(cls.ttwid_conf["url"]))

            except httpx.HTTPStatusError as e:
                # 捕获 httpx 的状态代码错误 (captures specific status code errors from httpx)
                raise APIResponseError(
                    f"HTTP Status Code {e.response.status_code}: {e.response.text}"
                )

            except APIError as e:
                e.display_error()
                time.sleep(2)
                exit(0)


class VerifyFpManager:
    base_str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    # placeholders = [8, 13, 18, 23]

    # @classmethod
    # def gen_verify_fp(cls) -> str:
    #     """
    #     生成verifyFp 与 s_v_web_id (Generate verifyFp)
    #     """

    #     base36 = num_to_base36(int(round(time.time() * 1000)))

    #     random_part = [cls.base_str[random.randint(0, 35)] for _ in range(36)]
    #     for idx in cls.placeholders:
    #         random_part[idx] = "_"
    #     random_part[14] = "4"

    #     return f"verify_{base36}_" + "".join(random_part)

    @classmethod
    def gen_verify_fp(cls) -> str:
        """
        生成verifyFp 与 s_v_web_id (Generate verifyFp)
        """
        base_str = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
        t = len(base_str)
        milliseconds = int(round(time.time() * 1000))
        base36 = ""
        while milliseconds > 0:
            remainder = milliseconds % 36
            if remainder < 10:
                base36 = str(remainder) + base36
            else:
                base36 = chr(ord("a") + remainder - 10) + base36
            milliseconds = int(milliseconds / 36)
        r = base36
        o = [""] * 36
        o[8] = o[13] = o[18] = o[23] = "_"
        o[14] = "4"

        for i in range(36):
            if not o[i]:
                n = 0 or int(random.random() * t)
                if i == 19:
                    n = 3 & n | 8
                o[i] = base_str[n]

        return "verify_" + r + "_" + "".join(o)

    @classmethod
    def gen_s_v_web_id(cls) -> str:
        return cls.gen_verify_fp()


class XBogusManager:
    @classmethod
    def str_2_endpoint(cls, endpoint: str) -> str:
        try:
            final_endpoint = XB().getXBogus(endpoint)
        except Exception as e:
            raise RuntimeError(_("生成X-Bogus失败: {0})").format(e))

        return final_endpoint[0]

    @classmethod
    def model_2_endpoint(cls, base_endpoint: str, params: dict) -> str:
        if not isinstance(params, dict):
            raise TypeError(_("参数必须是字典类型"))

        param_str = "&".join([f"{k}={v}" for k, v in params.items()])

        try:
            xb_value = XB().getXBogus(param_str)
        except Exception as e:
            raise RuntimeError(_("生成X-Bogus失败: {0})").format(e))

        # 检查base_endpoint是否已有查询参数 (Check if base_endpoint already has query parameters)
        separator = "&" if "?" in base_endpoint else "?"

        final_endpoint = f"{base_endpoint}{separator}{param_str}&X-Bogus={xb_value[1]}"

        return final_endpoint


class SecUserIdFetcher:
    # 预编译正则表达式
    _DOUYIN_URL_PATTERN = re.compile(r"user/([^/?]*)")
    _REDIRECT_URL_PATTERN = re.compile(r"sec_uid=([^&]*)")

    @classmethod
    async def get_sec_user_id(cls, url: str) -> str:
        """
        从单个url中获取sec_user_id (Get sec_user_id from a single url)

        Args:
            url (str): 输入的url (Input url)

        Returns:
            str: 匹配到的sec_user_id (Matched sec_user_id)。
        """

        if not isinstance(url, str):
            raise TypeError(_("参数必须是字符串类型"))

        # 提取有效URL
        url = str(extract_valid_urls(url))

        pattern = (
            cls._REDIRECT_URL_PATTERN
            if "v.douyin.com" in url
            else cls._DOUYIN_URL_PATTERN
        )

        try:
            transport = httpx.AsyncHTTPTransport(retries=5)
            async with httpx.AsyncClient(
                transport=transport, proxies=dict(TokenManager.proxies), timeout=10
            ) as client:
                response = await client.get(url, follow_redirects=True)

                if response.status_code in {200, 444}:
                    match = pattern.search(str(response.url))
                    if match:
                        return match.group(1)
                    else:
                        raise APIResponseError(_("未在响应的地址中找到sec_user_id, 检查链接是否为用户主页"))

                elif response.status_code == 401:
                    raise APIUnauthorizedError(_("未授权的请求"))
                elif response.status_code == 404:
                    raise APINotFoundError(_("未找到API端点"))
                elif response.status_code == 503:
                    raise APIUnavailableError(_("API服务不可用"))
                else:
                    raise APIError(_("API错误码：{0}").format(response.status_code))

        except APIError as e:
            e.display_error()
            logger.error(str(e))

        except httpx.RequestError:
            raise APIConnectionError(_("连接到API时发生错误，请检查链接"))

    @classmethod
    async def get_all_sec_user_id(cls, urls: list) -> list:
        """
        获取列表sec_user_id列表 (Get list sec_user_id list)

        Args:
            urls: list: 用户url列表 (User url list)

        Return:
            sec_user_ids: list: 用户sec_user_id列表 (User sec_user_id list)
        """

        if not isinstance(urls, list):
            raise TypeError(_("参数必须是列表类型"))

        # 提取有效URL
        urls = extract_valid_urls(urls)

        sec_user_ids = [cls.get_sec_user_id(url) for url in urls]
        return await asyncio.gather(*sec_user_ids)


class AwemeIdFetcher:
    # 预编译正则表达式
    _DOUYIN_VIDEO_URL_PATTERN = re.compile(r"video/([^/?]*)")
    _DOUYIN_NOTE_URL_PATTERN = re.compile(r"note/([^/?]*)")

    @classmethod
    async def get_aweme_id(cls, url: str) -> str:
        """
        从单个url中获取aweme_id (Get aweme_id from a single url)

        Args:
            url (str): 输入的url (Input url)

        Returns:
            str: 匹配到的aweme_id (Matched aweme_id)。
        """

        if not isinstance(url, str):
            raise TypeError(_("参数必须是字符串类型"))

        # 提取有效URL
        url = str(extract_valid_urls(url))

        # 重定向到完整链接
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, follow_redirects=True)
            url = str(response.url)

        video_pattern = cls._DOUYIN_VIDEO_URL_PATTERN
        note_pattern = cls._DOUYIN_NOTE_URL_PATTERN

        try:
            if video_pattern.search(url):
                match = video_pattern.search(url)
            elif note_pattern.search(url):
                match = note_pattern.search(url)
            else:
                raise APIResponseError(
                    _("未在响应的地址中找到aweme_id, 检查链接是否为作品页")
                )  # (aweme_id not found in the response address, check if the link is the work page)

            return match.group(1)

        except APIError as e:
            e.display_error()
            logger.error(str(e))

    @classmethod
    async def get_all_aweme_id(cls, urls: list) -> list:
        """
        获取视频aweme_id,传入列表url都可以解析出aweme_id (Get video aweme_id, pass in the list url can parse out aweme_id)

        Args:
            urls: list: 列表url (list url)

        Return:
            aweme_ids: list: 视频的唯一标识，返回列表 (The unique identifier of the video, return list)
        """

        if not isinstance(urls, list):
            raise TypeError(_("参数必须是列表类型"))

        # 提取有效URL
        urls = extract_valid_urls(urls)

        aweme_ids = [cls.get_aweme_id(url) for url in urls]
        return await asyncio.gather(*aweme_ids)


class MixIdFetcher:
    @classmethod
    async def get_mix_id(cls, url: str) -> str:
        pass


class WebCastIdFetcher:
    # 预编译正则表达式
    _DOUYIN_LIVE_URL_PATTERN = re.compile(r"live/([^/?]*)")
    # https://live.douyin.com/766545142636?cover_type=0&enter_from_merge=web_live&enter_method=web_card&game_name=&is_recommend=1&live_type=game&more_detail=&request_id=20231110224012D47CD00C18B4AE4BFF9B&room_id=7299828646049827596&stream_type=vertical&title_type=1&web_live_page=hot_live&web_live_tab=all
    # https://live.douyin.com/766545142636
    _DOUYIN_LIVE_URL_PATTERN2 = re.compile(r"https://live.douyin.com/(\d+)")
    # https://webcast.amemv.com/douyin/webcast/reflow/7318296342189919011?u_code=l1j9bkbd&did=MS4wLjABAAAAEs86TBQPNwAo-RGrcxWyCdwKhI66AK3Pqf3ieo6HaxI&iid=MS4wLjABAAAA0ptpM-zzoliLEeyvWOCUt-_dQza4uSjlIvbtIazXnCY&with_sec_did=1&use_link_command=1&ecom_share_track_params=&extra_params={"from_request_id":"20231230162057EC005772A8EAA0199906","im_channel_invite_id":"0"}&user_id=3644207898042206&liveId=7318296342189919011&from=share&style=share&enter_method=click_share&roomId=7318296342189919011&activity_info={}
    _DOUYIN_LIVE_URL_PATTERN3 = re.compile(r"reflow/([^/?]*)")

    @classmethod
    async def get_webcast_id(cls, url: str) -> str:
        """
        从单个url中获取webcast_id (Get webcast_id from a single url)

        Args:
            url (str): 输入的url (Input url)

        Returns:
            str: 匹配到的webcast_id (Matched webcast_id)。
        """

        if not isinstance(url, str):
            raise TypeError(_("参数必须是字符串类型"))

        # 提取有效URL
        url = extract_valid_urls(url)

        # 重定向到完整链接
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, follow_redirects=True)
            url = str(response.url)

        live_pattern = cls._DOUYIN_LIVE_URL_PATTERN
        live_pattern2 = cls._DOUYIN_LIVE_URL_PATTERN2
        live_pattern3 = cls._DOUYIN_LIVE_URL_PATTERN3

        try:
            if live_pattern.search(url):
                match = live_pattern.search(url)
            elif live_pattern2.search(url):
                match = live_pattern2.search(url)
            elif live_pattern3.search(url):
                match = live_pattern3.search(url)
                logger.debug(_("该链接返回的是room_id，请使用fetch_user_live_videos_by_room_id接口"))
            else:
                raise APIResponseError(_("未在响应的地址中找到webcast_id, 检查链接是否为直播页"))

            return match.group(1)

        except APIError as e:
            e.display_error()
            logger.error(str(e))

    @classmethod
    async def get_all_webcast_id(cls, urls: list) -> list:
        """
        获取直播webcast_id,传入列表url都可以解析出webcast_id (Get live webcast_id, pass in the list url can parse out webcast_id)

        Args:
            urls: list: 列表url (   list url)

        Return:
            webcast_ids: list: 直播的唯一标识，返回列表 (The unique identifier of the live, return list)
        """

        if not isinstance(urls, list):
            raise TypeError(_("参数必须是列表类型"))

        # 提取有效URL
        urls = extract_valid_urls(urls)

        webcast_ids = [cls.get_webcast_id(url) for url in urls]
        return await asyncio.gather(*webcast_ids)


def get_request_sizes(page_counts: int, max_counts: int) -> list[int]:
    """
    用于获取请求大小列表 (Used to get request size list)

    Args:
        page_counts: int: 每页视频数 (Number of videos per page)
        max_counts: int: 最大视频数 (Maximum number of videos)

    Return:
        requests: list[int]: 请求大小列表 (Request size list)
    """

    full_requests = max_counts // page_counts
    remainder = max_counts % page_counts

    requests = [page_counts] * full_requests
    if remainder:
        requests.append(remainder)

    return requests


def format_file_name(
    naming_template: str,
    aweme_data: dict = {},
    custom_fields: dict = {},
    desc_length_limit: int = 200,
) -> str:
    """
    根据配置文件的全局格式化文件名
    (Format file name according to the global conf file)

    Args:
        aweme_data (dict): 抖音数据的字典 (dict of douyin data)
        naming_template (str): 文件的命名模板, 如 "{create}_{desc}" (Naming template for files, such as "{create}_{desc}")
        custom_fields (dict): 用户自定义字段, 用于替代默认的字段值 (Custom fields for replacing default field values)
        desc_length_limit (int): 控制 'desc' 字段的长度限制 (Control the length limit of the 'desc' field)

    Note:
        windows 文件名长度限制为 255 个字符, 开启了长文件名支持后为 32,767 个字符
        (Windows file name length limit is 255 characters, 32,767 characters after long file name support is enabled)
        Unix 文件名长度限制为 255 个字符
        (Unix file name length limit is 255 characters)
        取去除后的20个字符, 加上后缀, 一般不会超过255个字符
        (Take the removed 20 characters, add the suffix, and generally not exceed 255 characters)

    Returns:
        str: 格式化的文件名 (Formatted file name)
    """
    # 如果字典中没有对应的键，则使用用户自定义的字段
    # (If there is no corresponding key in the dictionary, use the user-defined field)
    fields = {
        "create": "",
        "nickname": "",
        "aweme_id": "",
        "desc": "",
        "uid": "",
    }

    if custom_fields:
        fields.update(custom_fields)
    else:
        fields = {
            "create": aweme_data.get("create_time", ""),
            "nickname": aweme_data.get("nickname", ""),
            "aweme_id": aweme_data.get("aweme_id", ""),
            "desc": aweme_data.get("desc", ""),
            "uid": aweme_data.get("uid", ""),
        }

    # 处理 'desc' 字段的长度限制
    if desc_length_limit is not None and len(fields["desc"]) > desc_length_limit:
        half_limit = desc_length_limit // 2 - 6
        fields[
            "desc"
        ] = f"{fields['desc'][:half_limit]}......{fields['desc'][-half_limit:]}"

    return naming_template.format(**fields)


def create_user_folder(kwargs: dict, nickname: Union[str, int]) -> Path:
    """
    根据提供的配置文件和昵称，创建对应的保存目录。
    (Create the corresponding save directory according to the provided conf file and nickname.)

    Args:
        kwargs (dict): 配置文件，字典格式。(Conf file, dict format)
        nickname (Union[str, int]): 用户的昵称，允许字符串或整数。  (User nickname, allow strings or integers)

    Note:
        如果未在配置文件中指定路径，则默认为 "Download"。
        (If the path is not specified in the conf file, it defaults to "Download".)
        支持绝对与相对路径。
        (Support absolute and relative paths)

    Raises:
        TypeError: 如果 kwargs 不是字典格式，将引发 TypeError。
        (If kwargs is not in dict format, TypeError will be raised.)
    """

    # 确定函数参数是否正确
    if not isinstance(kwargs, dict):
        raise TypeError("kwargs 参数必须是字典")

    # 创建基础路径
    base_path = Path(kwargs.get("path", "Download"))

    # 添加下载模式和用户名
    user_path = (
        base_path / "douyin" / kwargs.get("mode", "PLEASE_SETUP_MODE") / str(nickname)
    )

    # 获取绝对路径并确保它存在
    resolve_user_path = user_path.resolve()

    # 创建目录
    resolve_user_path.mkdir(parents=True, exist_ok=True)

    return resolve_user_path


def rename_user_folder(old_path: Path, new_nickname: str) -> Path:
    """
    重命名用户目录 (Rename User Folder).

    Args:
        old_path (Path): 旧的用户目录路径 (Path of the old user folder)
        new_nickname (str): 新的用户昵称 (New user nickname)

    Returns:
        Path: 重命名后的用户目录路径 (Path of the renamed user folder)
    """
    # 获取目标目录的父目录 (Get the parent directory of the target folder)
    parent_directory = old_path.parent

    # 构建新目录路径 (Construct the new directory path)
    new_path = old_path.rename(parent_directory / new_nickname).resolve()

    return new_path


def create_or_rename_user_folder(
    kwargs: dict, local_user_data: dict, current_nickname: str
) -> Path:
    """
    创建或重命名用户目录 (Create or rename user directory)

    Args:
        kwargs (dict): 配置参数 (Conf parameters)
        local_user_data (dict): 本地用户数据 (Local user data)
        current_nickname (str): 当前用户昵称 (Current user nickname)

    Returns:
        user_path (Path): 用户目录路径 (User directory path)
    """
    user_path = create_user_folder(kwargs, current_nickname)

    if not local_user_data:
        return user_path

    if local_user_data.get("nickname") != current_nickname:
        # 昵称不一致，触发目录更新操作
        user_path = rename_user_folder(user_path, current_nickname)

    return user_path


def extract_desc_from_share_desc(desc: str, share_desc: str) -> str:
    """
    从share_desc中提取desc (Extract desc from share_desc)

    Args:
        desc (str): 作品的desc (desc of the work)
        share_desc (str): 作品的share_desc (share_desc of the work)

    Note:
        只针对由于接口参数构建存在低版本的情况适用
        (Only applicable to the case where the interface parameter construction exists in the low version)
    Returns:
        extracted (str): 提取的desc (Extracted desc)
    """
    # 如果desc只是空格（无论多少），直接返回
    if desc.strip() == "":
        return desc

    # 如果多次匹配说明desc在share_desc中出现多次，我们只需要最后一次匹配的结果
    indices = [i for i in range(len(share_desc)) if share_desc.startswith(desc, i)]
    if not indices:
        return desc

    # 取最后一次匹配的位置
    last_index = indices[-1]
    # 从找到的desc开始，提取之后的所有内容
    extracted = share_desc[last_index:]
    # 假设URL或其他不需要的内容都在 'https' 之前
    end_index = extracted.find("https")
    if end_index != -1:
        extracted = extracted[:end_index].strip()

    return extracted


def show_qrcode(qrcode_url: str, show_image: bool = False) -> None:
    """
    显示二维码

    Args:
        qrcode_url (str): 登录二维码链接
        show_image (bool): 是否显示图像，True 表示显示，False 表示在控制台显示
    """
    if show_image:
        # 创建并显示QR码图像
        qr_code_img = qrcode.make(qrcode_url)
        qr_code_img.show()
    else:
        # 在控制台以 ASCII 形式打印二维码
        qr = qrcode.QRCode()
        qr.add_data(qrcode_url)
        qr.make(fit=True)
        # 在控制台以 ASCII 形式打印二维码
        qr.print_ascii(invert=True)