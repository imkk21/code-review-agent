import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager

def run_demo():
    print("=" * 60)
    print("              APEX AI & DEVSYNC LIVE DEMO AGENT")
    print("=" * 60)
    print("Launching headed Chrome browser...")
    
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-gpu")
    
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    
    try:
        # 1. Open DevSync Frontend
        driver.get("http://localhost:5173")
        
        print("\n[STEP 1] Redirected to DevSync.")
        print("--> Please log in (Google or GitHub) in the opened Chrome window.")
        print("--> Once you have successfully logged in and see the Dashboard,")
        input("--> PRESS ENTER HERE to resume the automated demo...")
        
        # 2. Wait for workspace dashboard cards to load
        print("\n[STEP 2] Running automation. Locating workspaces...")
        wait = WebDriverWait(driver, 15)
        time.sleep(2)
        
        # Check if we have workspaces or if it's empty
        cards = driver.find_elements(By.CSS_SELECTOR, ".card")
        if not cards:
            print("No workspaces detected. Creating a temporary workspace 'Apex AI Demo'...")
            # Click "New Workspace" button
            new_ws_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., 'New Workspace') or contains(., 'Create Workspace')]"))
            )
            driver.execute_script("arguments[0].click();", new_ws_btn)
            time.sleep(1)
            
            # Fill out workspace form
            name_input = wait.until(
                EC.presence_of_element_located((By.ID, "workspace-name"))
            )
            name_input.send_keys("Apex AI Demo")
            
            desc_input = driver.find_element(By.ID, "workspace-description")
            desc_input.send_keys("Automated real-time code audit playground")
            
            # Select Python language button in the languages grid
            python_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(., '🐍')]"))
            )
            driver.execute_script("arguments[0].click();", python_btn)
            time.sleep(0.5)
            
            # Click submit button
            submit_btn = driver.find_element(By.XPATH, "//button[@type='submit' and contains(., 'Create Workspace')]")
            driver.execute_script("arguments[0].click();", submit_btn)
            print("Workspace 'Apex AI Demo' created successfully.")
            
            # Wait for dashboard reload
            time.sleep(3)
            # Find the card again
            workspace_card = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".card"))
            )
        else:
            workspace_card = cards[0]
            
        print("Workspace card found! Clicking to launch IDE...")
        driver.execute_script("arguments[0].click();", workspace_card)
        
        # 3. Wait for collaborative IDE workspace to mount
        print("\n[STEP 3] Entering collaborative IDE workspace...")
        wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".h-screen"))
        )
        time.sleep(3)
        
        # 4. Create a new test python file
        print("\n[STEP 4] Setting up file 'demo_security.py'...")
        # Check if it already exists in explorer list
        explorer_files = driver.find_elements(By.XPATH, "//span[contains(text(), 'demo_security.py')]")
        if explorer_files:
            print("File 'demo_security.py' already exists. Clicking to open it.")
            driver.execute_script("arguments[0].click();", explorer_files[0])
            time.sleep(1)
        else:
            # Click the "New File" button in explorer
            new_file_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='New File']"))
            )
            driver.execute_script("arguments[0].click();", new_file_btn)
            time.sleep(1)
            
            # Find input, type name, and hit enter
            new_file_input = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[placeholder='filename.ext']"))
            )
            new_file_input.send_keys("demo_security.py")
            new_file_input.send_keys(Keys.ENTER)
            print("File 'demo_security.py' created successfully.")
            time.sleep(2)
        
        # 5. Focus editor and write code
        print("\n[STEP 5] Typing vulnerable Python code into Monaco Editor...")
        monaco_editor = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".monaco-editor"))
        )
        driver.execute_script("arguments[0].click();", monaco_editor)
        time.sleep(0.5)
        
        # Clear editor (Ctrl+A then Backspace)
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys('a').key_up(Keys.CONTROL).perform()
        actions.send_keys(Keys.BACKSPACE).perform()
        time.sleep(0.5)
        
        # Type the vulnerable snippet
        vulnerable_code = (
            "import os\n\n"
            "# 1. Critical Hardcoded secret\n"
            "DB_PASS = 'KGAT_ea34dc35c5f3e3fef822bcbb14944036'\n\n"
            "# 2. Print debugging warning\n"
            "print('Debug: DB connection setup')\n"
        )
        
        # Type content
        for line in vulnerable_code.split('\n'):
            actions.send_keys(line).perform()
            actions.send_keys(Keys.ENTER).perform()
            time.sleep(0.1)
            
        print("Code typed in editor. Waiting 2.5 seconds for debounced auto-save & Apex AI review...")
        time.sleep(4.5)
        
        # 6. Toggle AI Auditor Sidebar Panel
        print("\n[STEP 6] Opening the right-side Apex AI Auditor sidebar panel...")
        ai_auditor_btn = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button[title='Toggle Apex AI Auditor Panel']"))
        )
        driver.execute_script("arguments[0].click();", ai_auditor_btn)
        time.sleep(2)
        
        print("\n[DEMO LIVE] You should now see:")
        print("1. Red squiggly lines under DB_PASS (Hardcoded secret) in Monaco Editor.")
        print("2. Amber squiggly lines under print statement (Print Statement Debugging).")
        print("3. Detailed explanations in the right-side sidebar panel.")
        print("\nApplying suggested refactoring patch in 5 seconds...")
        time.sleep(5)
        
        # 7. Apply AI Fix
        print("\n[STEP 7] Applying AI suggested patch...")
        apply_btn = wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Apply Fix')]"))
        )
        driver.execute_script("arguments[0].click();", apply_btn)
        print("Patch applied! Code replaced and saved automatically.")
        time.sleep(4)
        
        print("\n[DEMO COMPLETE] Real-time integration successfully executed!")
        print("Keeping the window open for 15 seconds so you can inspect...")
        time.sleep(15)
        
    except Exception as e:
        print(f"\n[ERROR] Automation encountered an issue: {e}")
        time.sleep(5)
    finally:
        print("Closing browser...")
        driver.quit()
        print("Demo closed.")

if __name__ == "__main__":
    run_demo()
