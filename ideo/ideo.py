import argparse
import contextlib
import json
import os
import time
from datetime import datetime
from http.cookies import SimpleCookie

from curl_cffi import requests
from curl_cffi.requests import Cookies
from fake_useragent import UserAgent

from ConfigCenter import R2Config
import jwt
from dotenv import load_dotenv
load_dotenv()


ua = UserAgent(browsers=["edge"])

base_url = "https://ideogram.ai"
browser_version = "edge101"
id_key = "AIzaSyBwq4bRiOapXYaKE-0Y46vLAw1-fzALq7Y"
user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
HEADERS = {
    "Origin": base_url,
    "Referer": base_url + "/",
    "DNT": "1",
    "Accept-Encoding": "gzip, deflate, br",
    "Content-Type": "application/json",
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "TE": "trailers",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) \
        Gecko/20100101 Firefox/117.0",
}

class ImageGen:
    def __init__(self) -> None:
        # R2Config requires env variables to be setup
        self.config = R2Config()
        self.config_file_name = 'ideo_token.json'
        self.config_cookie_file_name = 'ideo_cookie.txt'
        self.session: requests.Session = requests.Session()
        HEADERS["user-agent"] = ua.random
        self.cookie = ''
        self.user_id = ''
        self.auth_token = ''
        HEADERS["Authorization"] = f"Bearer {''}"
        self.session.headers = HEADERS
        self.check_and_refresh_auth_tokens()
        self.check_and_update_session_cookies(self.auth_token)
        
        #print(f'Headers:\n{self.session.headers}')
        
    ################################################################
    # Refresh Ideo Token and Session with R2ConfigCenter Start
    ################################################################
    def is_token_expired(self, acc_token):
        try:
            claims = jwt.decode(jwt=acc_token, algorithms=['HS256'], options={"verify_signature": False})
            exp = claims["exp"]
            now = datetime.now().timestamp()
            print(f"compare timestamp, exp:{exp}, now:{now}, result:{exp < now}")
            return exp < now
        except jwt.ExpiredSignatureError:
            return True
        except jwt.InvalidTokenError:
            return True
    
    def refresh_iss_tokens(self, refresh_token: str) -> dict:
        request_ref = "https://securetoken.googleapis.com/v1/token?key=" + id_key
        headers = {
            "Accept": "*/*",
            "Content-Type": "application/json; charset=UTF-8",
            "X-Client-Version": "Firefox/JsCore/9.23.0/FirebaseCore-web",
            "User-Agent": user_agent,
            "Origin": base_url,
        }
        data = json.dumps({"grantType": "refresh_token", "refreshToken": refresh_token})
        response_object = requests.post(
            request_ref,
            headers=headers,
            data=data,
            impersonate=browser_version,
        )
        response_object_json = response_object.json()
        tokens = {
            "user_id": response_object_json["user_id"],
            "access_token": response_object_json["access_token"],
            "refresh_token": response_object_json["refresh_token"],
        }
        print(f'Writing refreshed tokens to R2Config...')
        print(f'{tokens}')
        self.config.write_json(self.config_file_name, tokens)
        return tokens

    def check_and_refresh_auth_tokens(self) -> dict:
        tokens = self.config.read_json(file_name=self.config_file_name)
        if not tokens:
            error = f"Cannot read file '{self.config_file_name}' from config center. Put json with the field 'refresh_token' and save"
            print(error)
            raise Exception(error)
        refresh_token = tokens.get("refresh_token", None)
        if not refresh_token:
            print(f"No 'refresh_token' found in the {self.config_file_name}")
            return None
        acc_token = tokens.get("access_token", None)
        if not acc_token or self.is_token_expired(acc_token):
            print(f'No acc token found or expired. Refresh Token...')
            tokens = self.refresh_iss_tokens(refresh_token=refresh_token)
        else:
            print(f"Ideo Tokens still valid, user_id: {tokens['user_id']}, auth_token:{tokens['access_token']}")
        self.user_id = tokens['user_id']
        self.auth_token = tokens['access_token']
        self.session.headers["Authorization"] = f"Bearer {self.auth_token}"
        return tokens
    
    @staticmethod
    def cookies_to_header_string(cookies: dict) -> str:
        cookie_pairs = []
        for key, value in cookies.items():
            if key == "session_cookie":
                cookie_pairs.append(f"{key}={value}")
        return "; ".join(cookie_pairs)
    @staticmethod
    def parse_cookie_string(cookie_string):
        cookie = SimpleCookie()
        cookie.load(cookie_string)
        cookies_dict = {}
        for key, morsel in cookie.items():
            cookies_dict[key] = morsel.value
        #return Cookies(cookies_dict)
        return cookies_dict
    
    def check_and_update_session_cookies(self, iss_token: str) -> dict:
        cookie_str = None
        cookie_dict = None
        try:
            cookie_str = self.config.read_text(self.config_cookie_file_name)
            cookie_dict = ImageGen.parse_cookie_string(cookie_str)
        except Exception:
            print(f"Cannot find {self.config_cookie_file_name} in ConfigCenter")
            cookie_str = None
        
        if not cookie_dict or self.is_token_expired(cookie_dict["session_cookie"]):
            request_url = f"{base_url}/api/account/login"
            #self.session.headers["Authorization"] = f"Bearer {iss_token}"
            response_obj = requests.post(
                url=request_url,
                headers=self.session.headers,
                data=json.dumps({}),
                auth=("Bearer", iss_token),
            )
            if not response_obj.ok:
                print(response_obj.text)
                raise Exception(f"Error response {str(response_obj)}")
            cookie_dict = dict(response_obj.cookies)
            print(f'new cookie refreshed: \n {cookie_dict}')
            cookie_str = ImageGen.cookies_to_header_string(cookie_dict)
            self.config.write_text(file_name=self.config_cookie_file_name, text_content=cookie_str)
            print(f'New cookie saved to ConfigCenter...')
        else:
            print(f'cookie loaded successfully. No refresh needed.')
        print(f'Cookie saved to ImageGen...')
        self.session.cookies = Cookies(cookie_dict)
        print(f'Current cookies:\n{self.session.cookies}')
        self.cookie = cookie_str
        return cookie_dict
    ################################################################
    # Refresh Ideo Token and Session with R2ConfigCenter END
    ################################################################


    def get_limit_left(self) -> int:
        self.session.headers["user-agent"] = ua.random
        url = f"{base_url}/api/images/sampling_available_v2?model_version=V_0_3"
        r = self.session.get(url, impersonate=browser_version)
        if not r.ok:
            raise Exception("Can not get limit left.")
        data = r.json()

        return int(data["max_creations_per_day"]) - int(
            data["num_standard_generations_today"]
        )



    def _fetch_images_metadata(self, request_id):
        url = (
            f"https://ideogram.ai/api/images/retrieve_metadata_request_id/{request_id}"
        )
        response = self.session.get(url, impersonate=browser_version)
        data = response.json()
        # this is very interesting it use resolution to check if the image is ready
        if data.get("resolution") == 1024:
            return data
        else:
            return None

    def get_images(self, prompt: str, is_auto_prompt: str = "ON") -> list:
        url = f"{base_url}/api/images/sample"
        self.session.headers["user-agent"] = ua.random
        payload = {
            "aspect_ratio": "1:1",
            "model_version": "V_0_3",  # the latest version
            "private": False,
            "prompt": prompt,
            "raw_or_fun": "raw",
            "sampling_speed": 0,
            "style": "photo",
            "user_id": self.user_id,
            "variation_strength": 50,
            "use_autoprompt_option": is_auto_prompt,  # "AUTO" or "OFF"
        }
        print(f'Post images playload:\n{payload}')
        response = self.session.post(
            url,
            data=json.dumps(payload),
            impersonate=browser_version,
        )
        if not response.ok:
            print(response.text)
            raise Exception(f"Error response {str(response)}")
        response_body = response.json()
        request_id = response_body["request_id"]
        start_wait = time.time()
        print("Waiting for results...")
        while True:
            if int(time.time() - start_wait) > 600:
                raise Exception("Request timeout")
            image_data = self._fetch_images_metadata(request_id)
            if not image_data:
                print(".", end="", flush=True)
            else:
                data = image_data.get("responses", [])
                return [
                    f"{base_url}/api/images/direct/{i['response_id']}" for i in data
                ]

    def save_images(
        self,
        prompt: str,
        output_dir: str,
    ) -> None:
        png_index = 0
        try:
            links = self.get_images(prompt)
        except Exception as e:
            print(e)
            raise
        with contextlib.suppress(FileExistsError):
            os.mkdir(output_dir)
        print()
        for link in links:
            while os.path.exists(os.path.join(output_dir, f"{png_index}.png")):
                png_index += 1
            print(link)
            response = self.session.get(link, impersonate=browser_version)
            if response.status_code != 200:
                raise Exception("Could not download image")
            # save response to file
            with open(
                os.path.join(output_dir, f"{png_index}.png"), "wb"
            ) as output_file:
                output_file.write(response.content)
            png_index += 1


if __name__ == "__main__":
    #main()
    ideo = ImageGen()
    #tokens = ideo.check_and_refresh_auth_tokens()
    #print(ideo.cookie)
    images = ideo.get_images('No Cookie need to be refreshed')
    print(images)

    limit = ideo.get_limit_left()
    print(f'limit: {limit}')