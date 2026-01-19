"""
Secure password generation utilities.
"""

import secrets
import string
import re
import math
from typing import List, Dict, Optional
from config import DEFAULT_PASSWORD_LENGTH, PASSWORD_CHARSET, MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH


class PasswordGenerator:
    """Generates secure random passwords."""
    
    @staticmethod
    def generate_password(length: int = DEFAULT_PASSWORD_LENGTH, 
                         include_lowercase: bool = True,
                         include_uppercase: bool = True,
                         include_digits: bool = True,
                         include_symbols: bool = True) -> str:
        """
        Generate a secure random password.
        
        Args:
            length: Length of password (8-100)
            include_lowercase: Include lowercase letters
            include_uppercase: Include uppercase letters
            include_digits: Include digits
            include_symbols: Include symbols
            
        Returns:
            Generated password
            
        Raises:
            ValueError: If no character types are selected or length is invalid
        """
        if length < MIN_PASSWORD_LENGTH or length > MAX_PASSWORD_LENGTH:
            raise ValueError(f"Password length must be between {MIN_PASSWORD_LENGTH} and {MAX_PASSWORD_LENGTH}")
        
        # Build character pool
        char_pool = ""
        requirements = {}
        
        if include_lowercase:
            char_pool += PASSWORD_CHARSET['lowercase']
            requirements['lowercase'] = PASSWORD_CHARSET['lowercase']
        
        if include_uppercase:
            char_pool += PASSWORD_CHARSET['uppercase']
            requirements['uppercase'] = PASSWORD_CHARSET['uppercase']
        
        if include_digits:
            char_pool += PASSWORD_CHARSET['digits']
            requirements['digits'] = PASSWORD_CHARSET['digits']
        
        if include_symbols:
            char_pool += PASSWORD_CHARSET['symbols']
            requirements['symbols'] = PASSWORD_CHARSET['symbols']
        
        if not char_pool:
            raise ValueError("At least one character type must be selected")
        
        # Ensure at least one character from each selected type
        password_chars = []
        
        # Add one character from each required type
        for charset in requirements.values():
            password_chars.append(secrets.choice(charset))
        
        # Fill remaining length with random characters from the pool
        remaining_length = length - len(password_chars)
        if remaining_length > 0:
            password_chars.extend(secrets.choice(char_pool) for _ in range(remaining_length))
        
        # Shuffle the characters
        secrets.SystemRandom().shuffle(password_chars)
        
        return ''.join(password_chars)
    
    @staticmethod
    def generate_passphrase(num_words: int = 4, separator: str = "-") -> str:
        """
        Generate a passphrase using a small word list.
        
        Args:
            num_words: Number of words in passphrase (3-8)
            separator: Word separator
            
        Returns:
            Generated passphrase
        """
        if num_words < 3 or num_words > 8:
            raise ValueError("Number of words must be between 3 and 8")
        
        # Simple word list (in production, use a larger list)
        word_list = [
            "apple", "brave", "cloud", "dragon", "eagle", "flame", "globe", "honey",
            "island", "jungle", "knight", "lunar", "mountain", "nova", "ocean", "planet",
            "quantum", "river", "star", "tiger", "unicorn", "volcano", "whale", "xray",
            "yellow", "zebra", "alpha", "beta", "gamma", "delta"
        ]
        
        words = [secrets.choice(word_list) for _ in range(num_words)]
        
        # Capitalize some words and add numbers/symbols for strength
        if secrets.randbelow(2):
            words[secrets.randbelow(num_words)] = words[secrets.randbelow(num_words)].upper()
        
        # Add a number
        words.append(str(secrets.randbelow(100)))
        
        # Add a symbol
        symbols = list("!@#$%^&*")
        words.append(secrets.choice(symbols))
        
        # Shuffle
        secrets.SystemRandom().shuffle(words)
        
        return separator.join(words)
    
    @staticmethod
    def calculate_entropy(password: str) -> float:
        """
        Calculate password entropy in bits.
        
        Args:
            password: Password to analyze
            
        Returns:
            Entropy in bits
        """
        if not password:
            return 0.0
        
        # Determine character pool size
        char_pool_size = 0
        if any(c.islower() for c in password):
            char_pool_size += 26
        if any(c.isupper() for c in password):
            char_pool_size += 26
        if any(c.isdigit() for c in password):
            char_pool_size += 10
        if any(c in PASSWORD_CHARSET['symbols'] for c in password):
            char_pool_size += len(PASSWORD_CHARSET['symbols'])
        
        # If we couldn't determine, use conservative estimate
        if char_pool_size == 0:
            char_pool_size = 26  # Assume lowercase only
        
        # Calculate entropy using the formula: L * log2(N)
        # where L is password length, N is character pool size
        try:
            entropy = len(password) * math.log2(char_pool_size)
        except ValueError:
            # Fallback in case log2 fails
            entropy = len(password) * math.log(char_pool_size, 2)
        
        return entropy
    
    @staticmethod
    def evaluate_strength(password: str) -> Dict[str, any]:
        """
        Evaluate password strength.
        
        Args:
            password: Password to evaluate
            
        Returns:
            Dictionary with strength evaluation
        """
        if not password:
            return {"strength": "Very Weak", "score": 0, "entropy": 0.0, "length": 0, "feedback": []}
        
        score = 0
        feedback = []
        
        # Length check
        if len(password) >= 12:
            score += 2
        elif len(password) >= 8:
            score += 1
        else:
            feedback.append("Password is too short (minimum 8 characters)")
        
        # Character variety checks
        if re.search(r'[a-z]', password):
            score += 1
        else:
            feedback.append("Add lowercase letters")
        
        if re.search(r'[A-Z]', password):
            score += 1
        else:
            feedback.append("Add uppercase letters")
        
        if re.search(r'\d', password):
            score += 1
        else:
            feedback.append("Add numbers")
        
        if re.search(f'[{re.escape(PASSWORD_CHARSET["symbols"])}]', password):
            score += 1
        else:
            feedback.append("Add symbols")
        
        # Entropy check
        entropy = PasswordGenerator.calculate_entropy(password)
        if entropy > 80:
            score += 2
        elif entropy > 60:
            score += 1
        
        # Common patterns to avoid
        common_patterns = [
            '123456', 'password', 'qwerty', 'admin', 'welcome',
            'letmein', 'monkey', 'dragon', 'baseball', 'football'
        ]
        
        password_lower = password.lower()
        for pattern in common_patterns:
            if pattern in password_lower:
                score -= 2
                feedback.append(f"Avoid common pattern '{pattern}'")
                break
        
        # Determine strength level
        if score >= 7:
            strength = "Very Strong"
        elif score >= 5:
            strength = "Strong"
        elif score >= 3:
            strength = "Moderate"
        elif score >= 1:
            strength = "Weak"
        else:
            strength = "Very Weak"
        
        return {
            "strength": strength,
            "score": score,
            "entropy": entropy,
            "length": len(password),
            "feedback": feedback,
            "has_lowercase": bool(re.search(r'[a-z]', password)),
            "has_uppercase": bool(re.search(r'[A-Z]', password)),
            "has_digits": bool(re.search(r'\d', password)),
            "has_symbols": bool(re.search(f'[{re.escape(PASSWORD_CHARSET["symbols"])}]', password))
        }
    
    @staticmethod
    def generate_multiple_passwords(count: int = 5, length: int = DEFAULT_PASSWORD_LENGTH, 
                                   **kwargs) -> List[str]:
        """
        Generate multiple passwords.
        
        Args:
            count: Number of passwords to generate (1-20)
            length: Length of each password
            **kwargs: Additional arguments for generate_password
            
        Returns:
            List of generated passwords
        """
        if count < 1 or count > 20:
            raise ValueError("Count must be between 1 and 20")
        
        return [PasswordGenerator.generate_password(length, **kwargs) for _ in range(count)]