import sys
sys.path.insert(0, r'C:\QuantLab\Data_Lab')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\shared\config')
sys.path.insert(0, r'C:\QuantLab\Data_Lab\tools')

from datetime import datetime

from scratch.dashboard_cta.diet_cta_dashboard import main


if __name__ == "__main__":
    main()
    print(f"Diet CTA Dashboard updated: {datetime.now().strftime('%Y-%m-%d %I:%M %p')}")