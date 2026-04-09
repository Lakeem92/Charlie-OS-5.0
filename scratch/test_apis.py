"""
API Configuration Test Script
Test all API keys and configurations
"""

from config.api_config import APIConfig
from config.api_clients import (
    AlpacaClient,
    SECEdgarClient,
    CoinGeckoClient,
    FMPClient,
    AlphaVantageClient,
    FREDClient,
    SchwabClient,
    TiingoClient
)


def test_api_keys():
    """Test that all API keys are loaded"""
    print("\n" + "="*70)
    print("API KEY VALIDATION TEST")
    print("="*70 + "\n")
    
    APIConfig.print_status()
    
    validation = APIConfig.validate_keys()
    all_valid = all(validation.values())
    
    if all_valid:
        print("\n✓ All API keys loaded successfully!\n")
        return True
    else:
        print("\n✗ Some API keys are missing. Check your .env file.\n")
        return False


def test_api_clients():
    """Test API client initialization"""
    print("\n" + "="*70)
    print("API CLIENT INITIALIZATION TEST")
    print("="*70 + "\n")
    
    clients = {
        'Alpaca': AlpacaClient,
        'SEC EDGAR': SECEdgarClient,
        'CoinGecko': CoinGeckoClient,
        'Financial Modeling Prep': FMPClient,
        'Alpha Vantage': AlphaVantageClient,
        'FRED': FREDClient,
        'Charles Schwab': SchwabClient,
        'Tiingo': TiingoClient,
    }
    
    results = {}
    for name, ClientClass in clients.items():
        try:
            client = ClientClass()
            results[name] = True
            print(f"✓ {name:30s} Client initialized")
        except Exception as e:
            results[name] = False
            print(f"✗ {name:30s} Failed: {str(e)}")
    
    all_success = all(results.values())
    if all_success:
        print("\n✓ All API clients initialized successfully!\n")
    else:
        print("\n✗ Some API clients failed to initialize.\n")
    
    return all_success


def test_sample_requests():
    """Test sample API requests (optional - may use API quota)"""
    print("\n" + "="*70)
    print("SAMPLE API REQUEST TEST (Optional)")
    print("="*70 + "\n")
    
    print("Skipping live API tests to preserve API quotas.")
    print("To test live requests, uncomment the test code in this function.\n")
    
    # Uncomment to test live requests:
    """
    try:
        # Test FMP quote
        fmp = FMPClient()
        quote = fmp.get_quote('AAPL')
        print(f"✓ FMP API: Retrieved AAPL quote")
        
        # Test FRED series
        fred = FREDClient()
        gdp = fred.get_series('GDP')
        print(f"✓ FRED API: Retrieved GDP data")
        
        # Test CoinGecko
        coingecko = CoinGeckoClient()
        btc = coingecko.get_coin_price('bitcoin')
        print(f"✓ CoinGecko API: Retrieved Bitcoin price")
        
        print("\n✓ All sample API requests successful!\n")
        
    except Exception as e:
        print(f"\n✗ Sample request failed: {str(e)}\n")
    """


def main():
    """Run all tests"""
    print("\n" + "="*70)
    print("DATA LAB API CONFIGURATION TEST SUITE")
    print("="*70)
    
    # Test 1: API Keys
    keys_valid = test_api_keys()
    
    # Test 2: Client Initialization
    clients_valid = test_api_clients()
    
    # Test 3: Sample Requests (optional)
    test_sample_requests()
    
    # Final Summary
    print("="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"API Keys Valid:        {'✓ PASS' if keys_valid else '✗ FAIL'}")
    print(f"Clients Initialized:   {'✓ PASS' if clients_valid else '✗ FAIL'}")
    print("="*70 + "\n")
    
    if keys_valid and clients_valid:
        print("🎉 All tests passed! Your API configuration is ready to use.\n")
        print("Example usage:")
        print("  from config.api_clients import FMPClient")
        print("  client = FMPClient()")
        print("  quote = client.get_quote('BABA')")
        print()
    else:
        print("⚠️  Some tests failed. Please check your .env file and API keys.\n")


if __name__ == '__main__':
    main()
