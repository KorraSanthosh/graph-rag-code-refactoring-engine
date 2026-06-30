# This is a messy file designed to be refactored
import os

def helper_one(x):
    return x * 2

def helper_two(y):
    return y + 10

def process_data():
    # Messy logic with deep nesting and poor naming
    data = [1, 2, 3, 4, 5]
    result = []
    for item in data:
        if item > 2:
            val = helper_one(item)
            val = helper_two(val)
            result.append(val)
    
    # Just to make it runnable for verification
    print(f"Processed result: {result}")
    return result

if __name__ == "__main__":
    process_data()
