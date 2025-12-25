"""
Core game logic and classes
"""

import pygame
import math
from config import *

class HitObject:
    """Base class for hit objects (circles, sliders, spinners)"""
    
    def __init__(self, x, y, time, object_type="circle"):
        self.x = x
        self.y = y
        self.time = time  # Time when object should be hit (in ms)
        self.object_type = object_type  # "circle", "slider", "spinner"
        self.hit = False
        self.hit_accuracy = None
        self.color = COLOR_CIRCLE
        
        if object_type == "slider":
            self.color = COLOR_SLIDER
        elif object_type == "spinner":
            self.color = COLOR_SPINNER
    
    def draw(self, surface, current_time):
        """Draw the hit object"""
        if self.hit:
            return
        
        time_until_hit = self.time - current_time
        
        # Don't draw if too far in the future
        if time_until_hit > PREEMPT_TIME:
            return
        
        # Calculate opacity based on time until hit
        opacity = 1.0
        if time_until_hit < FADE_OUT_TIME:
            opacity = max(0, time_until_hit / FADE_OUT_TIME)
        
        # Calculate scale based on approach
        scale = (PREEMPT_TIME - time_until_hit) / PREEMPT_TIME
        radius = int(CIRCLE_RADIUS * (1 + scale * 0.5))
        
        if self.object_type == "spinner":
            radius = int(SPINNER_RADIUS * (1 + scale * 0.3))
        
        # Create a surface with alpha for transparency
        obj_surface = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
        color_with_alpha = (*self.color, int(255 * opacity))
        
        if self.object_type == "circle":
            pygame.draw.circle(obj_surface, color_with_alpha, (radius, radius), radius)
            pygame.draw.circle(obj_surface, (255, 255, 255, int(100 * opacity)), (radius, radius), radius, 2)
        
        elif self.object_type == "spinner":
            pygame.draw.circle(obj_surface, color_with_alpha, (radius, radius), radius)
            pygame.draw.circle(obj_surface, (255, 255, 255, int(100 * opacity)), (radius, radius), radius, 3)
        
        elif self.object_type == "slider":
            pygame.draw.circle(obj_surface, color_with_alpha, (radius, radius), radius)
        
        surface.blit(obj_surface, (int(self.x - radius), int(self.y - radius)))
    
    def check_hit(self, current_time):
        """Check if object was hit and return accuracy"""
        if self.hit:
            return None
        
        time_diff = abs(self.time - current_time)
        
        if time_diff <= HIT_WINDOW_PERFECT:
            return "perfect"
        elif time_diff <= HIT_WINDOW_GREAT:
            return "great"
        elif time_diff <= HIT_WINDOW_OKAY:
            return "okay"
        elif time_diff <= HIT_WINDOW_MISS:
            return "miss"
        
        return None


class Score:
    """Manages score, combo, and accuracy tracking"""
    
    def __init__(self):
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect_hits = 0
        self.great_hits = 0
        self.okay_hits = 0
        self.misses = 0
        self.accuracy = 0.0
    
    def add_hit(self, accuracy):
        """Add a hit and update score"""
        if accuracy == "perfect":
            self.score += SCORE_PERFECT
            self.perfect_hits += 1
            self.combo += 1
        elif accuracy == "great":
            self.score += SCORE_GREAT
            self.great_hits += 1
            self.combo += 1
        elif accuracy == "okay":
            self.score += SCORE_OKAY
            self.okay_hits += 1
            self.combo += 1
        elif accuracy == "miss":
            self.score += SCORE_MISS
            self.misses += 1
            self.combo = 0
        
        # Update max combo
        if self.combo > self.max_combo:
            self.max_combo = self.combo
        
        # Calculate accuracy
        self.update_accuracy()
    
    def update_accuracy(self):
        """Calculate current accuracy percentage"""
        total_hits = self.perfect_hits + self.great_hits + self.okay_hits + self.misses
        if total_hits == 0:
            self.accuracy = 0.0
            return
        
        accuracy_points = (self.perfect_hits * 300 + self.great_hits * 100 + self.okay_hits * 50)
        self.accuracy = (accuracy_points / (total_hits * 300)) * 100
    
    def get_accuracy_string(self):
        """Get formatted accuracy string"""
        return f"{self.accuracy:.2f}%"
    
    def reset(self):
        """Reset score"""
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.perfect_hits = 0
        self.great_hits = 0
        self.okay_hits = 0
        self.misses = 0
        self.accuracy = 0.0


class Game:
    """Main game class"""
    
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.hit_objects = []
        self.score = Score()
        self.current_time = 0
        self.start_time = pygame.time.get_ticks()
        self.paused = False
        self.game_over = False
        
        # Initialize with some demo hit objects
        self.create_demo_beatmap()
        
        self.font_small = pygame.font.Font(None, 24)
        self.font_large = pygame.font.Font(None, 48)
    
    def create_demo_beatmap(self):
        """Create a simple demo beatmap"""
        # Add some hit objects in a pattern
        times = [500, 1000, 1500, 2000, 2500, 3000, 3500, 4000, 4500, 5000]
        
        for i, t in enumerate(times):
            x = PLAYFIELD_X + PLAYFIELD_WIDTH // 2 + math.sin(i * 0.5) * 100
            y = PLAYFIELD_Y + PLAYFIELD_HEIGHT // 2
            obj_type = ["circle", "circle", "slider"][i % 3]
            self.hit_objects.append(HitObject(x, y, t, obj_type))
    
    def handle_event(self, event):
        """Handle input events"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                self.check_clicks(pygame.mouse.get_pos())
        
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_z or event.key == pygame.K_x:
                self.check_clicks(pygame.mouse.get_pos())
            elif event.key == pygame.K_SPACE:
                self.paused = not self.paused
    
    def check_clicks(self, pos):
        """Check if a click hits any objects"""
        click_x, click_y = pos
        
        for obj in self.hit_objects:
            if obj.hit:
                continue
            
            distance = math.sqrt((obj.x - click_x) ** 2 + (obj.y - click_y) ** 2)
            
            if distance <= CIRCLE_RADIUS + 20:  # Hit zone slightly larger than circle
                accuracy = obj.check_hit(self.current_time)
                if accuracy:
                    obj.hit = True
                    obj.hit_accuracy = accuracy
                    self.score.add_hit(accuracy)
    
    def update(self):
        """Update game state"""
        if not self.paused:
            self.current_time = pygame.time.get_ticks() - self.start_time
        
        # Check for missed objects
        for obj in self.hit_objects:
            if not obj.hit and self.current_time > obj.time + HIT_WINDOW_MISS:
                obj.hit = True
                self.score.add_hit("miss")
        
        # Check if game is over (all objects processed)
        if all(obj.hit for obj in self.hit_objects):
            self.game_over = True
    
    def draw(self, surface):
        """Draw game state"""
        # Draw playfield border
        pygame.draw.rect(surface, COLOR_PLAYFIELD, 
                        (PLAYFIELD_X, PLAYFIELD_Y, PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT), 0)
        pygame.draw.rect(surface, (200, 200, 200),
                        (PLAYFIELD_X, PLAYFIELD_Y, PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT), 2)
        
        # Draw hit zone line
        hit_zone_y = PLAYFIELD_Y + PLAYFIELD_HEIGHT - 50
        pygame.draw.line(surface, COLOR_HIT_ZONE, (PLAYFIELD_X, hit_zone_y),
                        (PLAYFIELD_X + PLAYFIELD_WIDTH, hit_zone_y), 3)
        
        # Draw hit objects
        for obj in self.hit_objects:
            obj.draw(surface, self.current_time)
        
        # Draw score info
        score_text = self.font_large.render(str(self.score.score), True, COLOR_TEXT)
        surface.blit(score_text, (20, 20))
        
        combo_text = self.font_small.render(f"Combo: {self.score.combo}", True, COLOR_TEXT)
        surface.blit(combo_text, (20, 60))
        
        accuracy_text = self.font_small.render(self.score.get_accuracy_string(), True, COLOR_TEXT)
        surface.blit(accuracy_text, (20, 85))
        
        time_text = self.font_small.render(f"Time: {self.current_time // 1000}s", True, COLOR_TEXT)
        surface.blit(time_text, (20, 110))
        
        # Draw pause message
        if self.paused:
            pause_text = self.font_large.render("PAUSED", True, COLOR_PERFECT)
            surface.blit(pause_text, (self.width // 2 - 100, self.height // 2 - 50))
        
        # Draw game over message
        if self.game_over:
            game_over_text = self.font_large.render("GAME OVER", True, COLOR_PERFECT)
            surface.blit(game_over_text, (self.width // 2 - 150, self.height // 2 - 50))
            
            final_score_text = self.font_small.render(f"Final Score: {self.score.score}", True, COLOR_TEXT)
            surface.blit(final_score_text, (self.width // 2 - 100, self.height // 2 + 20))
            
            max_combo_text = self.font_small.render(f"Max Combo: {self.score.max_combo}", True, COLOR_TEXT)
            surface.blit(max_combo_text, (self.width // 2 - 100, self.height // 2 + 50))
