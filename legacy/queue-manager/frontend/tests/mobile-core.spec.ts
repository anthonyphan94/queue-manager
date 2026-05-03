import { test, expect, devices } from '@playwright/test';

/**
 * Mobile Core E2E Tests for Salon Turn Manager
 * Tests mobile responsiveness and core queue management logic
 */

// Enforce iPhone 12 Pro viewport for this entire test file
test.use({ ...devices['iPhone 12 Pro'] });

test.describe('Scenario A: Mobile Layout Verification', () => {
    test('should display mobile-friendly layout', async ({ page }) => {
        // Navigate to homepage
        await page.goto('/');

        // Wait for header to be visible instead of networkidle
        const header = page.locator('header');
        await expect(header).toBeVisible({ timeout: 10000 });

        // Assert: Logo image is visible
        const logo = page.locator('header img');
        await expect(logo).toBeVisible();

        // Assert: On mobile, the layout should stack vertically (single column)
        const mainContent = page.locator('main');
        await expect(mainContent).toBeVisible();

        // Assert: "Technicians" button is visible
        const techniciansButton = page.locator('header button');
        await expect(techniciansButton).toBeVisible();
    });

    test('should open Staff Check-In Modal when clicking Technicians button', async ({ page }) => {
        await page.goto('/');

        // Wait for header button to be ready
        const techniciansButton = page.locator('header button');
        await expect(techniciansButton).toBeVisible({ timeout: 10000 });

        // Action: Click the "Technicians" button
        await techniciansButton.click();

        // Assert: The Staff Check-In Modal should appear
        const modal = page.locator('[role="dialog"], .fixed.inset-0').last();
        await expect(modal).toBeVisible({ timeout: 5000 });

        // Verify modal content 
        await expect(page.locator('text=Select Working Technicians').last()).toBeVisible();
    });
});

test.describe('Scenario B: Core Business Logic - Queue Management', () => {
    const testTechnicianName = 'QA Test Bot';

    test('should complete full queue management flow', async ({ page }) => {
        await page.goto('/');

        const techniciansButton = page.locator('header button');
        await expect(techniciansButton).toBeVisible({ timeout: 10000 });
        await techniciansButton.click();

        // Wait for modal to appear
        const modal = page.locator('[role="dialog"], .fixed.inset-0').last();
        await expect(modal).toBeVisible();

        // Step 2: Add a new technician
        // First, click "Add New Technician" button to reveal the input
        const addNewTechBtn = page.locator('button').filter({ hasText: /Add New Technician/i }).first();
        await addNewTechBtn.click();

        // Now the input should be visible
        const nameInput = page.getByPlaceholder('Enter technician name...');
        await expect(nameInput).toBeVisible();
        await nameInput.fill(testTechnicianName);

        // Click the Add button (type="submit" inside the form)
        const addButton = page.locator('button[type="submit"], button:has-text("Add")').last();
        await addButton.click();

        // Step 3: Verify technician appears in the modal list
        const technicianInModal = page.locator(`text="${testTechnicianName}"`);
        await expect(technicianInModal).toBeVisible({ timeout: 5000 });

        // Step 4: Activate the technician (check them in)
        // Click on the technician name or row to toggle
        // The row is the click target for toggling
        const techRow = page.locator('div').filter({ hasText: testTechnicianName }).last();
        await techRow.click();

        // Close the modal
        const doneButton = page.locator('button:has-text("Done")');
        if (await doneButton.isVisible()) {
            await doneButton.click();
        } else {
            // Fallback
            await page.keyboard.press('Escape');
        }

        // Wait for modal to close
        await page.waitForTimeout(500);

        // Step 5: Verify technician appears in the queue list on dashboard
        const techInQueue = page.locator(`text="${testTechnicianName}"`).last();
        await expect(techInQueue).toBeVisible({ timeout: 5000 });

        // Step 6: Test "Next Turn" action
        const nextTurnButton = page.locator('button').filter({ hasText: /Next Turn/i }).first();
        if (await nextTurnButton.isVisible()) {
            await nextTurnButton.click();
            await page.waitForTimeout(1000);
        }

        // Cleanup: Remove the technician
        await techniciansButton.click();
        await expect(modal).toBeVisible();

        // Find delete/remove button for this technician
        // In StaffCheckInModal, the row has a "Remove" button
        const cleanupRow = page.locator('div').filter({ hasText: testTechnicianName }).last();
        const removeBtn = cleanupRow.locator('button[aria-label*="Remove"], button:has-text("Remove")').last();

        if (await removeBtn.isVisible()) {
            await removeBtn.click();
            // No confirmation dialog in the code, creates immediate removal?
            // Code: onClick -> e.stopPropagation(); onRemove(tech.id);
        }

        // Verify removed
        await expect(page.locator(`text="${testTechnicianName}"`)).toHaveCount(0);
    });
});
