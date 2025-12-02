"""
영업 리드 이메일 크롤러
- 구글시트에서 회사 정보 읽기
- 네이버 플레이스/지도에서 이메일 검색
- 회사 홈페이지에서 이메일 추출
- 결과를 구글시트에 자동 업데이트
"""

import gspread
from google.oauth2.service_account import Credentials
import requests
from bs4 import BeautifulSoup
import re
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EmailCrawler:
    def __init__(self, spreadsheet_key, credentials_file):
        """
        이메일 크롤러 초기화
        
        Args:
            spreadsheet_key: 구글 시트 ID
            credentials_file: 구글 서비스 계정 인증 파일 경로
        """
        self.spreadsheet_key = spreadsheet_key
        self.credentials_file = credentials_file
        self.sheet = None
        self.driver = None
        
        # 이메일 정규표현식 패턴
        self.email_pattern = re.compile(
            r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        )
        
    def connect_google_sheet(self):
        """구글 시트 연결"""
        try:
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scope
            )
            client = gspread.authorize(creds)
            self.sheet = client.open_by_key(self.spreadsheet_key).sheet1
            logger.info("✅ 구글 시트 연결 성공")
            return True
        except Exception as e:
            logger.error(f"❌ 구글 시트 연결 실패: {e}")
            return False
    
    def setup_selenium(self):
        """Selenium 웹드라이버 설정"""
        try:
            from selenium.webdriver.chrome.service import Service
            from webdriver_manager.chrome import ChromeDriverManager
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 백그라운드 실행
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
            
            # webdriver-manager로 자동 설치
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            logger.info("✅ Selenium 드라이버 설정 완료")
            return True
        except Exception as e:
            logger.error(f"❌ Selenium 설정 실패: {e}")
            return False
    
    def search_naver_place(self, company_name):
        """
        네이버 플레이스/지도에서 회사 정보 검색
        
        Args:
            company_name: 회사명
            
        Returns:
            dict: {email, homepage, phone}
        """
        try:
            search_url = f"https://search.naver.com/search.naver?query={company_name}"
            self.driver.get(search_url)
            time.sleep(2)
            
            result = {
                'email': None,
                'homepage': None,
                'phone': None
            }
            
            # 플레이스 정보 찾기
            try:
                # 전화번호
                phone_elements = self.driver.find_elements(By.CSS_SELECTOR, '.tel, .phone, [class*="tel"]')
                if phone_elements:
                    result['phone'] = phone_elements[0].text.strip()
                
                # 홈페이지 URL
                homepage_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[href*="http"]')
                for elem in homepage_elements:
                    href = elem.get_attribute('href')
                    if href and 'naver.com' not in href and 'google.com' not in href:
                        result['homepage'] = href
                        break
                
                # 페이지 소스에서 이메일 추출
                page_source = self.driver.page_source
                emails = self.email_pattern.findall(page_source)
                
                # 네이버 관련 이메일 제외
                valid_emails = [
                    email for email in emails 
                    if 'naver.com' not in email and 'google.com' not in email
                ]
                
                if valid_emails:
                    result['email'] = valid_emails[0]
                
            except Exception as e:
                logger.warning(f"플레이스 정보 추출 중 오류: {e}")
            
            return result
            
        except Exception as e:
            logger.error(f"네이버 검색 실패 ({company_name}): {e}")
            return {'email': None, 'homepage': None, 'phone': None}
    
    def extract_email_from_website(self, url):
        """
        회사 홈페이지에서 이메일 추출
        
        Args:
            url: 홈페이지 URL
            
        Returns:
            str: 이메일 주소 또는 None
        """
        try:
            if not url:
                return None
            
            # URL 정규화
            if not url.startswith('http'):
                url = 'http://' + url
            
            self.driver.get(url)
            time.sleep(2)
            
            # 연락처/Contact 페이지 찾기
            contact_links = self.driver.find_elements(
                By.XPATH, 
                "//a[contains(text(), '연락') or contains(text(), 'Contact') or contains(text(), '회사소개')]"
            )
            
            if contact_links:
                contact_links[0].click()
                time.sleep(2)
            
            # 페이지에서 이메일 추출
            page_source = self.driver.page_source
            emails = self.email_pattern.findall(page_source)
            
            # 유효한 이메일 필터링 (info@, ceo@, contact@ 등 우선)
            priority_keywords = ['ceo', 'info', 'contact', 'admin', 'master']
            
            for keyword in priority_keywords:
                for email in emails:
                    if keyword in email.lower():
                        return email
            
            # 우선순위 키워드가 없으면 첫 번째 이메일 반환
            if emails:
                return emails[0]
            
            return None
            
        except Exception as e:
            logger.warning(f"홈페이지 이메일 추출 실패 ({url}): {e}")
            return None
    
    def find_email(self, company_name, representative=None):
        """
        회사 이메일 찾기 (네이버 + 홈페이지)
        
        Args:
            company_name: 회사명
            representative: 대표자명 (선택)
            
        Returns:
            dict: {email, source, confidence}
        """
        logger.info(f"🔍 검색 시작: {company_name}")
        
        result = {
            'email': None,
            'source': None,
            'confidence': 'LOW'
        }
        
        # 1단계: 네이버 플레이스/지도 검색
        naver_result = self.search_naver_place(company_name)
        
        if naver_result['email']:
            result['email'] = naver_result['email']
            result['source'] = '네이버 플레이스'
            result['confidence'] = 'HIGH'
            logger.info(f"✅ 네이버에서 이메일 발견: {result['email']}")
            return result
        
        # 2단계: 홈페이지에서 이메일 추출
        if naver_result['homepage']:
            website_email = self.extract_email_from_website(naver_result['homepage'])
            if website_email:
                result['email'] = website_email
                result['source'] = '회사 홈페이지'
                result['confidence'] = 'MEDIUM'
                logger.info(f"✅ 홈페이지에서 이메일 발견: {result['email']}")
                return result
        
        logger.warning(f"⚠️ 이메일을 찾지 못함: {company_name}")
        return result
    
    def add_email_column(self):
        """구글시트에 이메일 컬럼 추가"""
        try:
            # 현재 헤더 가져오기
            headers = self.sheet.row_values(1)
            
            # 이미 이메일 컬럼이 있는지 확인
            if '대표이메일(자동수집)' in headers:
                logger.info("이메일 컬럼이 이미 존재합니다")
                return headers.index('대표이메일(자동수집)') + 1
            
            # 새 컬럼 추가 (I 컬럼 다음)
            new_col_index = len(headers) + 1
            self.sheet.update_cell(1, new_col_index, '대표이메일(자동수집)')
            self.sheet.update_cell(1, new_col_index + 1, '수집출처')
            self.sheet.update_cell(1, new_col_index + 2, '신뢰도')
            
            logger.info(f"✅ 이메일 컬럼 추가 완료 (컬럼 {new_col_index})")
            return new_col_index
            
        except Exception as e:
            logger.error(f"❌ 컬럼 추가 실패: {e}")
            return None
    
    def crawl_all_companies(self, start_row=2, end_row=None):
        """
        전체 회사 리스트 크롤링
        
        Args:
            start_row: 시작 행 (기본값: 2, 헤더 제외)
            end_row: 종료 행 (None이면 전체)
        """
        try:
            # 이메일 컬럼 추가
            email_col = self.add_email_column()
            if not email_col:
                return
            
            # 전체 데이터 가져오기
            all_data = self.sheet.get_all_values()
            
            if end_row is None:
                end_row = len(all_data)
            
            total_count = end_row - start_row + 1
            success_count = 0
            
            logger.info(f"📊 총 {total_count}개 회사 크롤링 시작")
            
            for idx in range(start_row - 1, end_row):
                row_num = idx + 1
                row_data = all_data[idx]
                
                # 회사명 (B열)
                company_name = row_data[1] if len(row_data) > 1 else None
                # 대표자명 (C열)
                representative = row_data[2] if len(row_data) > 2 else None
                
                if not company_name:
                    continue
                
                logger.info(f"\n[{row_num - 1}/{total_count}] 처리 중: {company_name}")
                
                # 이메일 검색
                result = self.find_email(company_name, representative)
                
                # 결과 업데이트
                if result['email']:
                    self.sheet.update_cell(row_num, email_col, result['email'])
                    self.sheet.update_cell(row_num, email_col + 1, result['source'])
                    self.sheet.update_cell(row_num, email_col + 2, result['confidence'])
                    success_count += 1
                else:
                    self.sheet.update_cell(row_num, email_col, '미발견')
                    self.sheet.update_cell(row_num, email_col + 2, 'NONE')
                
                # API 제한 방지를 위한 대기
                time.sleep(3)
            
            logger.info(f"\n✅ 크롤링 완료!")
            logger.info(f"📊 성공: {success_count}/{total_count} ({success_count/total_count*100:.1f}%)")
            
        except Exception as e:
            logger.error(f"❌ 크롤링 중 오류 발생: {e}")
            raise
    
    def close(self):
        """리소스 정리"""
        if self.driver:
            self.driver.quit()
            logger.info("✅ 브라우저 종료")


def main():
    """메인 실행 함수"""
    
    try:
        from config import Config
        
        # 설정 유효성 검사
        Config.validate()
        
        logger.info("=" * 60)
        logger.info("🚀 이메일 크롤러 시작")
        logger.info("=" * 60)
        logger.info(f"📊 구글 시트 ID: {Config.SPREADSHEET_KEY[:20]}...")
        logger.info(f"🔑 인증 파일: {Config.CREDENTIALS_FILE}")
        logger.info(f"⏱️  크롤링 딜레이: {Config.CRAWL_DELAY}초")
        logger.info("=" * 60)
        
        # 크롤러 초기화
        crawler = EmailCrawler(
            spreadsheet_key=Config.SPREADSHEET_KEY,
            credentials_file=Config.CREDENTIALS_FILE
        )
        
        # 구글 시트 연결
        if not crawler.connect_google_sheet():
            logger.error("구글 시트 연결 실패. 프로그램을 종료합니다.")
            return
        
        # Selenium 설정
        if not crawler.setup_selenium():
            logger.error("Selenium 설정 실패. 프로그램을 종료합니다.")
            return
        
        # 전체 크롤링 실행
        logger.info("\n📝 크롤링을 시작합니다...\n")
        crawler.crawl_all_companies(start_row=Config.START_ROW)
        
        logger.info("\n" + "=" * 60)
        logger.info("✅ 모든 작업이 완료되었습니다!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.info("\n⚠️ 사용자에 의해 중단되었습니다")
    except FileNotFoundError as e:
        logger.error(f"❌ 파일을 찾을 수 없습니다: {e}")
        logger.error("💡 .env 파일과 credentials.json 파일을 확인해주세요")
    except ValueError as e:
        logger.error(f"❌ 설정 오류: {e}")
        logger.error("💡 .env 파일의 SPREADSHEET_KEY를 확인해주세요")
    except Exception as e:
        logger.error(f"❌ 예상치 못한 오류 발생: {e}")
        import traceback
        logger.error(traceback.format_exc())
    finally:
        if 'crawler' in locals():
            crawler.close()


if __name__ == "__main__":
    main()
