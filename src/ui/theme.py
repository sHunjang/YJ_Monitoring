# ==============================================
# UI 테마 설정 (화이트 모드)
# ==============================================
"""
Material Design 기반 화이트 모드 테마

색상 체계:
- 배경: 밝은 회색 계열
- 강조: 파란색 (전력), 초록색 (환경)
- 텍스트: 어두운 회색/검정
"""

from PyQt6.QtGui import QFont


class Theme:
    """화이트 모드 테마 정의"""
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 색상 (Material Design Light)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    # 배경색
    BG_PRIMARY = '#f5f5f5'      # 메인 배경 (밝은 회색)
    BG_SECONDARY = '#ffffff'    # 사이드바/카드 배경 (흰색)
    BG_TERTIARY = '#e3f2fd'     # 호버/선택 배경 (연한 파랑)
    
    # 강조색
    PRIMARY = '#1976d2'         # 메인 강조 (파란색)
    SECONDARY = '#d32f2f'       # 경고/오류 (빨강)
    SUCCESS = '#388e3c'         # 성공 (초록)
    WARNING = '#f57c00'         # 주의 (주황)
    
    # 텍스트색
    TEXT_PRIMARY = '#212121'    # 메인 텍스트 (거의 검정)
    TEXT_SECONDARY = '#757575'  # 보조 텍스트 (회색)
    TEXT_DISABLED = '#bdbdbd'   # 비활성 텍스트
    
    # 센서 타입별 색상
    POWER_COLOR = '#1976d2'     # 전력 (파란색)
    HEATPUMP_COLOR = '#388e3c'  # 히트펌프 (초록색)
    PIPE_COLOR = '#f57c00'      # 지중배관 (주황색)
    
    # 차트 색상
    CHART_LINE = '#1976d2'      # 차트 선
    CHART_GRID = '#e0e0e0'      # 그리드 선
    CHART_AXIS = '#757575'      # 축 색상
    
    # 경계선
    BORDER = '#e0e0e0'          # 테두리
    DIVIDER = '#eeeeee'         # 구분선
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 폰트
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    FONT_FAMILY = 'Malgun Gothic'  # 한글 폰트
    
    @staticmethod
    def font(size=10, bold=False):
        """
        폰트 생성
        
        Args:
            size: 폰트 크기 (pt)
            bold: 굵게 여부
        
        Returns:
            QFont: 폰트 객체
        """
        font = QFont(Theme.FONT_FAMILY, size)
        if bold:
            font.setBold(True)
        return font
    
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # 스타일시트 (CSS)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    @staticmethod
    def get_main_stylesheet():
        """메인 윈도우 스타일시트"""
        return f"""
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 메인 윈도우 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QMainWindow {{
                background-color: {Theme.BG_PRIMARY};
            }}
            
            QWidget {{
                background-color: {Theme.BG_PRIMARY};
                color: {Theme.TEXT_PRIMARY};
                font-family: {Theme.FONT_FAMILY};
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 카드 (QGroupBox) */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QGroupBox {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 12px;
                margin-top: 12px;
                padding: 20px;
                font-size: 14px;
                font-weight: bold;
                color: {Theme.TEXT_PRIMARY};
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 5px 10px;
                color: {Theme.PRIMARY};
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 버튼 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QPushButton {{
                background-color: {Theme.PRIMARY};
                border: none;
                border-radius: 8px;
                padding: 10px 20px;
                color: white;
                font-size: 13px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: #1565c0;
            }}
            
            QPushButton:pressed {{
                background-color: #0d47a1;
            }}
            
            QPushButton:checked {{
                background-color: {Theme.SUCCESS};
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 레이블 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QLabel {{
                color: {Theme.TEXT_PRIMARY};
                background-color: transparent;
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 테이블 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QTableWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 8px;
                gridline-color: {Theme.DIVIDER};
                color: {Theme.TEXT_PRIMARY};
            }}
            
            QTableWidget::item {{
                padding: 8px;
                border: none;
            }}
            
            QTableWidget::item:selected {{
                background-color: {Theme.BG_TERTIARY};
                color: {Theme.TEXT_PRIMARY};
            }}
            
            QHeaderView::section {{
                background-color: {Theme.BG_PRIMARY};
                color: {Theme.TEXT_PRIMARY};
                border: none;
                border-bottom: 2px solid {Theme.PRIMARY};
                padding: 10px;
                font-weight: bold;
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 트리 위젯 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QTreeWidget {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 8px;
                color: {Theme.TEXT_PRIMARY};
            }}
            
            QTreeWidget::item {{
                padding: 5px;
            }}
            
            QTreeWidget::item:hover {{
                background-color: {Theme.BG_TERTIARY};
            }}
            
            QTreeWidget::item:selected {{
                background-color: {Theme.PRIMARY};
                color: white;
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 라디오 버튼 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QRadioButton {{
                color: {Theme.TEXT_PRIMARY};
                spacing: 8px;
            }}
            
            QRadioButton::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 9px;
                border: 2px solid {Theme.BORDER};
                background-color: {Theme.BG_SECONDARY};
            }}
            
            QRadioButton::indicator:checked {{
                background-color: {Theme.PRIMARY};
                border: 2px solid {Theme.PRIMARY};
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 체크박스 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QCheckBox {{
                color: {Theme.TEXT_PRIMARY};
                spacing: 8px;
            }}
            
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 3px;
                border: 2px solid {Theme.BORDER};
                background-color: {Theme.BG_SECONDARY};
            }}
            
            QCheckBox::indicator:checked {{
                background-color: {Theme.PRIMARY};
                border: 2px solid {Theme.PRIMARY};
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 스크롤바 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QScrollBar:vertical {{
                background-color: {Theme.BG_PRIMARY};
                width: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: {Theme.BORDER};
                border-radius: 6px;
                min-height: 20px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: {Theme.PRIMARY};
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            
            QScrollBar:horizontal {{
                background-color: {Theme.BG_PRIMARY};
                height: 12px;
                border-radius: 6px;
            }}
            
            QScrollBar::handle:horizontal {{
                background-color: {Theme.BORDER};
                border-radius: 6px;
                min-width: 20px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background-color: {Theme.PRIMARY};
            }}
            
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 콤보박스 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QComboBox {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 5px;
                padding: 5px 10px;
                color: {Theme.TEXT_PRIMARY};
            }}
            
            QComboBox:hover {{
                border: 1px solid {Theme.PRIMARY};
            }}
            
            QComboBox::drop-down {{
                border: none;
                width: 30px;
            }}
            
            QComboBox::down-arrow {{
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid {Theme.TEXT_PRIMARY};
                margin-right: 10px;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                selection-background-color: {Theme.BG_TERTIARY};
                selection-color: {Theme.TEXT_PRIMARY};
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 입력 필드 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QLineEdit {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 5px;
                padding: 5px 10px;
                color: {Theme.TEXT_PRIMARY};
            }}
            
            QLineEdit:focus {{
                border: 1px solid {Theme.PRIMARY};
            }}
            
            QTextEdit {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 5px;
                padding: 5px 10px;
                color: {Theme.TEXT_PRIMARY};
            }}
            
            QTextEdit:focus {{
                border: 1px solid {Theme.PRIMARY};
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 탭 위젯 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QTabWidget::pane {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
                border-radius: 5px;
            }}
            
            QTabBar::tab {{
                background-color: {Theme.BG_PRIMARY};
                border: 1px solid {Theme.BORDER};
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 8px 15px;
                margin-right: 2px;
                color: {Theme.TEXT_SECONDARY};
            }}
            
            QTabBar::tab:selected {{
                background-color: {Theme.BG_SECONDARY};
                color: {Theme.PRIMARY};
                font-weight: bold;
            }}
            
            QTabBar::tab:hover {{
                background-color: {Theme.BG_TERTIARY};
            }}
            
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            /* 메뉴바 */
            /* ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━ */
            QMenuBar {{
                background-color: {Theme.BG_SECONDARY};
                color: {Theme.TEXT_PRIMARY};
                border-bottom: 1px solid {Theme.BORDER};
            }}
            
            QMenuBar::item {{
                background-color: transparent;
                padding: 5px 10px;
            }}
            
            QMenuBar::item:selected {{
                background-color: {Theme.BG_TERTIARY};
            }}
            
            QMenu {{
                background-color: {Theme.BG_SECONDARY};
                border: 1px solid {Theme.BORDER};
            }}
            
            QMenu::item {{
                padding: 5px 30px 5px 10px;
            }}
            
            QMenu::item:selected {{
                background-color: {Theme.BG_TERTIARY};
            }}
        """


# ==============================================
# 테스트 코드
# ==============================================
if __name__ == "__main__":
    print("=" * 70)
    print("테마 설정 테스트")
    print("=" * 70)
    
    print(f"\n[색상]")
    print(f"  PRIMARY: {Theme.PRIMARY}")
    print(f"  SUCCESS: {Theme.SUCCESS}")
    print(f"  WARNING: {Theme.WARNING}")
    
    print(f"\n[폰트]")
    font = Theme.font(12, bold=True)
    print(f"  Family: {font.family()}")
    print(f"  Size: {font.pointSize()}")
    print(f"  Bold: {font.bold()}")
    
    print("\n" + "=" * 70)
    print("✓ 테스트 완료")
    print("=" * 70)
