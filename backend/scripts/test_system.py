#!/usr/bin/env python3
"""
System test script for the Adaptive Boss Behavior System
"""

import sys
import os
import asyncio
import json
import time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.adaptive_boss_service import AdaptiveBossService
from app.services.embedding_service import EmbeddingService
from app.services.faiss_service import FAISSService
from app.services.jigsawstack_service import JigsawStackService
from app.models import PlayerContextData, BossActionRequest, ActionOutcomeData, GameActionOutcome
from app.database import SessionLocal
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SystemTester:
    """Test the entire adaptive boss system"""
    
    def __init__(self):
        self.adaptive_service = AdaptiveBossService()
        self.embedding_service = EmbeddingService()
        self.faiss_service = FAISSService()
        self.jigsawstack_service = JigsawStackService()
        self.db = SessionLocal()
        
        # Test game configuration
        self.test_game = {
            "game_id": "test_rpg_001",
            "name": "Test RPG",
            "description": "A test RPG for system validation",
            "vocabulary": {
                "game_name": "Test RPG",
                "boss_actions": [
                    "sword_slash", "fire_breath", "ground_slam", "magic_missile",
                    "defensive_stance", "rage_mode", "teleport_strike"
                ],
                "action_types": ["attack", "defend", "special", "magic"],
                "environments": ["arena", "forest", "cave"],
                "difficulty_levels": ["easy", "normal", "hard"]
            }
        }
    
    def test_embedding_service(self):
        """Test embedding generation"""
        logger.info("🧪 Testing Embedding Service...")
        
        try:
            # Create test player context
            player_context = PlayerContextData(
                frequent_actions=["dodge", "attack"],
                dodge_frequency=0.7,
                attack_patterns=["combo_attack"],
                movement_style="aggressive",
                reaction_time=0.3,
                health_percentage=0.8,
                difficulty_preference="normal",
                session_duration=10.0,
                recent_deaths=1,
                equipment_level=5
            )
            
            # Generate embedding
            embedding = self.embedding_service.create_context_embedding(player_context)
            logger.info(f"✅ Embedding generated: shape {embedding.shape}")
            
            # Test context hash
            context_hash = self.embedding_service.create_context_hash(player_context)
            logger.info(f"✅ Context hash generated: {context_hash[:16]}...")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Embedding service test failed: {str(e)}")
            return False
    
    def test_faiss_service(self):
        """Test FAISS vector operations"""
        logger.info("🧪 Testing FAISS Service...")
        
        try:
            game_id = self.test_game["game_id"]
            
            # Create test embeddings
            test_contexts = []
            for i in range(3):
                context = PlayerContextData(
                    frequent_actions=["dodge", "attack"],
                    dodge_frequency=0.5 + i * 0.1,
                    attack_patterns=["combo_attack"],
                    movement_style="aggressive",
                    reaction_time=0.3 + i * 0.1,
                    health_percentage=0.8,
                    difficulty_preference="normal",
                    session_duration=10.0,
                    recent_deaths=i,
                    equipment_level=5
                )
                test_contexts.append(context)
            
            # Generate embeddings
            embeddings = self.embedding_service.batch_create_embeddings(test_contexts)
            logger.info(f"✅ Generated {len(embeddings)} test embeddings")
            
            # Add to FAISS index
            for i, (context, embedding) in enumerate(zip(test_contexts, embeddings)):
                self.faiss_service.add_context(
                    game_id,
                    i + 1,  # context_id
                    embedding,
                    context.model_dump(),
                    0.7 + i * 0.1  # effectiveness_score
                )
            
            logger.info("✅ Added contexts to FAISS index")
            
            # Test similarity search
            query_embedding = embeddings[0]
            similar_contexts = self.faiss_service.search_similar_contexts(
                game_id, query_embedding, k=2
            )
            
            logger.info(f"✅ Found {len(similar_contexts)} similar contexts")
            
            # Test index stats
            stats = self.faiss_service.get_index_stats(game_id)
            logger.info(f"✅ Index stats: {stats}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ FAISS service test failed: {str(e)}")
            return False
    
    def test_jigsawstack_service(self):
        """Test JigsawStack integration"""
        logger.info("🧪 Testing JigsawStack Service...")
        
        try:
            # Create prompt for test game
            prompt_id = self.jigsawstack_service.create_boss_behavior_prompt(
                self.test_game["game_id"],
                self.test_game["vocabulary"]
            )
            
            logger.info(f"✅ Created JigsawStack prompt: {prompt_id}")
            
            # Test boss action generation
            player_context = PlayerContextData(
                frequent_actions=["dodge", "attack"],
                dodge_frequency=0.7,
                attack_patterns=["combo_attack"],
                movement_style="aggressive",
                reaction_time=0.3,
                health_percentage=0.8,
                difficulty_preference="normal",
                session_duration=10.0,
                recent_deaths=1,
                equipment_level=5
            )
            
            similar_contexts = [
                {
                    'context_id': 1,
                    'context_data': player_context.model_dump(),
                    'effectiveness_score': 0.8,
                    'similarity_score': 0.9
                }
            ]
            
            boss_action = self.jigsawstack_service.generate_boss_action(
                prompt_id,
                player_context,
                similar_contexts,
                0.8,  # boss_health
                "opening",  # battle_phase
                "arena"  # environment
            )
            
            logger.info(f"✅ Generated boss action: {boss_action.boss_action}")
            logger.info(f"   Action type: {boss_action.action_type}")
            logger.info(f"   Intensity: {boss_action.intensity}")
            
            # Clean up - delete the test prompt
            self.jigsawstack_service.delete_prompt(prompt_id)
            logger.info("✅ Cleaned up test prompt")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ JigsawStack service test failed: {str(e)}")
            return False
    
    def test_full_system_integration(self):
        """Test the complete system integration"""
        logger.info("🧪 Testing Full System Integration...")
        
        try:
            # Register test game
            result = self.adaptive_service.register_game(
                self.test_game["game_id"],
                self.test_game["name"],
                self.test_game["description"],
                self.test_game["vocabulary"],
                self.db
            )
            
            if not result["success"]:
                logger.error(f"Failed to register game: {result['message']}")
                return False
            
            logger.info("✅ Game registered successfully")
            
            # Generate boss action
            player_context = PlayerContextData(
                frequent_actions=["dodge", "attack", "block"],
                dodge_frequency=0.6,
                attack_patterns=["combo_attack", "hit_and_run"],
                movement_style="balanced",
                reaction_time=0.4,
                health_percentage=0.7,
                difficulty_preference="normal",
                session_duration=15.0,
                recent_deaths=2,
                equipment_level=4
            )
            
            request = BossActionRequest(
                game_id=self.test_game["game_id"],
                player_context=player_context,
                boss_health_percentage=0.8,
                battle_phase="mid_battle",
                environment_factors={"environment": "arena"}
            )
            
            boss_action = self.adaptive_service.generate_boss_action(request, self.db)
            logger.info(f"✅ Generated boss action: {boss_action.boss_action}")
            
            # Simulate action outcome logging
            # Note: In a real scenario, you'd get the action_id from the database
            # For testing, we'll use a dummy ID
            outcome = ActionOutcomeData(
                action_id=1,
                outcome=GameActionOutcome.SUCCESS,
                effectiveness_score=0.8,
                damage_dealt=25.0,
                player_hit=True,
                execution_time=1.2
            )
            
            # This would normally work with a real action_id
            # self.adaptive_service.log_action_outcome(outcome, self.db)
            # logger.info("✅ Action outcome logged")
            
            # Get game stats
            stats = self.adaptive_service.get_game_stats(self.test_game["game_id"], self.db)
            logger.info(f"✅ Game stats retrieved: {json.dumps(stats, indent=2)}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Full system integration test failed: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all system tests"""
        logger.info("🚀 Starting Adaptive Boss Behavior System Tests")
        logger.info("=" * 60)
        
        tests = [
            ("Embedding Service", self.test_embedding_service),
            ("FAISS Service", self.test_faiss_service),
            ("JigsawStack Service", self.test_jigsawstack_service),
            ("Full System Integration", self.test_full_system_integration)
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            logger.info(f"\n{'='*20} {test_name} {'='*20}")
            start_time = time.time()
            
            try:
                success = test_func()
                duration = time.time() - start_time
                results[test_name] = {
                    "success": success,
                    "duration": duration
                }
                
                if success:
                    logger.info(f"✅ {test_name} PASSED ({duration:.2f}s)")
                else:
                    logger.error(f"❌ {test_name} FAILED ({duration:.2f}s)")
                    
            except Exception as e:
                duration = time.time() - start_time
                results[test_name] = {
                    "success": False,
                    "duration": duration,
                    "error": str(e)
                }
                logger.error(f"❌ {test_name} CRASHED ({duration:.2f}s): {str(e)}")
        
        # Summary
        logger.info("\n" + "="*60)
        logger.info("📊 TEST SUMMARY")
        logger.info("="*60)
        
        passed = sum(1 for r in results.values() if r["success"])
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result["success"] else "❌ FAIL"
            logger.info(f"{status} {test_name} ({result['duration']:.2f}s)")
            if not result["success"] and "error" in result:
                logger.info(f"      Error: {result['error']}")
        
        logger.info(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            logger.info("🎉 All tests passed! System is ready for use.")
        else:
            logger.warning("⚠️  Some tests failed. Please check the configuration and dependencies.")
        
        return passed == total
    
    def cleanup(self):
        """Clean up test resources"""
        try:
            self.db.close()
            logger.info("✅ Test cleanup completed")
        except Exception as e:
            logger.warning(f"⚠️  Cleanup warning: {str(e)}")


def main():
    """Main test function"""
    tester = SystemTester()
    
    try:
        success = tester.run_all_tests()
        sys.exit(0 if success else 1)
    finally:
        tester.cleanup()


if __name__ == "__main__":
    main()