import requests
import sys
import json
from datetime import datetime

class PingPongAPITester:
    def __init__(self, base_url="https://pingpong-masters-1.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name, success, details=""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED: {details}")
        
        self.test_results.append({
            "test": name,
            "success": success,
            "details": details
        })

    def test_health_check(self):
        """Test basic API health"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Response: {data}"
            self.log_test("Health Check", success, details)
            return success
        except Exception as e:
            self.log_test("Health Check", False, str(e))
            return False

    def test_root_endpoint(self):
        """Test root API endpoint"""
        try:
            response = requests.get(f"{self.api_url}/", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Message: {data.get('message', 'No message')}"
            self.log_test("Root Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("Root Endpoint", False, str(e))
            return False

    def test_create_player(self, player_name="TestPlayer"):
        """Test player creation"""
        try:
            payload = {"name": player_name}
            response = requests.post(f"{self.api_url}/players", json=payload, timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Player ID: {data.get('id', 'No ID')}, Name: {data.get('name', 'No name')}"
                return data
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Create Player", success, details)
            return data if success else None
        except Exception as e:
            self.log_test("Create Player", False, str(e))
            return None

    def test_get_player(self, player_name):
        """Test getting player by name"""
        try:
            response = requests.get(f"{self.api_url}/players/{player_name}", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Player: {data.get('name', 'No name')}, Wins: {data.get('consecutive_wins', 0)}"
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Get Player", success, details)
            return success
        except Exception as e:
            self.log_test("Get Player", False, str(e))
            return False

    def test_create_game_session(self):
        """Test game session creation"""
        try:
            game_data = {
                "mode": "single_player",
                "player1_name": "TestPlayer",
                "player2_name": None,
                "winner": "TestPlayer",
                "player1_score": 5,
                "player2_score": 3,
                "bot_difficulty": "medium",
                "game_duration": 120
            }
            
            response = requests.post(f"{self.api_url}/games", json=game_data, timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Game ID: {data.get('id', 'No ID')}, Winner: {data.get('winner', 'No winner')}"
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Create Game Session", success, details)
            return success
        except Exception as e:
            self.log_test("Create Game Session", False, str(e))
            return False

    def test_get_recent_games(self):
        """Test getting recent games"""
        try:
            response = requests.get(f"{self.api_url}/games", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Games count: {len(data)}"
                if data:
                    details += f", Latest game winner: {data[0].get('winner', 'No winner')}"
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Get Recent Games", success, details)
            return success
        except Exception as e:
            self.log_test("Get Recent Games", False, str(e))
            return False

    def test_leaderboard(self):
        """Test leaderboard endpoints"""
        try:
            # Test consecutive wins leaderboard
            response = requests.get(f"{self.api_url}/leaderboard", timeout=10)
            success1 = response.status_code == 200
            details1 = f"Consecutive wins - Status: {response.status_code}"
            
            if success1:
                data = response.json()
                details1 += f", Players: {len(data)}"
                if data:
                    details1 += f", Top player: {data[0].get('name', 'No name')} ({data[0].get('consecutive_wins', 0)} wins)"
            
            # Test best streaks leaderboard
            response2 = requests.get(f"{self.api_url}/leaderboard/best-streaks", timeout=10)
            success2 = response2.status_code == 200
            details2 = f"Best streaks - Status: {response2.status_code}"
            
            if success2:
                data2 = response2.json()
                details2 += f", Players: {len(data2)}"
                if data2:
                    details2 += f", Top streak: {data2[0].get('name', 'No name')} ({data2[0].get('best_streak', 0)} wins)"
            
            success = success1 and success2
            details = f"{details1} | {details2}"
            
            self.log_test("Leaderboard Endpoints", success, details)
            return success
        except Exception as e:
            self.log_test("Leaderboard Endpoints", False, str(e))
            return False

    def test_multiplayer_game(self):
        """Test multiplayer game session"""
        try:
            # Create second player
            player2_data = self.test_create_player("TestPlayer2")
            if not player2_data:
                self.log_test("Multiplayer Game Setup", False, "Failed to create second player")
                return False
            
            # Create multiplayer game
            game_data = {
                "mode": "multiplayer",
                "player1_name": "TestPlayer",
                "player2_name": "TestPlayer2",
                "winner": "TestPlayer2",
                "player1_score": 3,
                "player2_score": 5,
                "bot_difficulty": None,
                "game_duration": 180
            }
            
            response = requests.post(f"{self.api_url}/games", json=game_data, timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                data = response.json()
                details += f", Multiplayer game created, Winner: {data.get('winner', 'No winner')}"
            else:
                details += f", Error: {response.text}"
                
            self.log_test("Multiplayer Game Session", success, details)
            return success
        except Exception as e:
            self.log_test("Multiplayer Game Session", False, str(e))
            return False

    def run_all_tests(self):
        """Run comprehensive API tests"""
        print("🏓 Starting Ping Pong API Tests...")
        print("=" * 50)
        
        # Basic connectivity tests
        if not self.test_health_check():
            print("❌ Health check failed - API may be down")
            return False
            
        if not self.test_root_endpoint():
            print("❌ Root endpoint failed")
            return False
        
        # Player management tests
        player_data = self.test_create_player("TestPlayer")
        if player_data:
            self.test_get_player("TestPlayer")
        
        # Game session tests
        self.test_create_game_session()
        self.test_get_recent_games()
        
        # Leaderboard tests
        self.test_leaderboard()
        
        # Multiplayer tests
        self.test_multiplayer_game()
        
        # Print summary
        print("\n" + "=" * 50)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed - check details above")
            return False

def main():
    tester = PingPongAPITester()
    success = tester.run_all_tests()
    
    # Save detailed results
    results = {
        "timestamp": datetime.now().isoformat(),
        "total_tests": tester.tests_run,
        "passed_tests": tester.tests_passed,
        "success_rate": (tester.tests_passed / tester.tests_run) * 100 if tester.tests_run > 0 else 0,
        "test_details": tester.test_results
    }
    
    with open('/app/backend_test_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())