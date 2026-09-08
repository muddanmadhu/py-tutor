/**
 * Accessibility and responsiveness checks.
 *
 * These are deliberately behavioural rather than a generic axe sweep: they
 * verify the things the specification asks for — keyboard navigation, focus
 * management, a working skip link, labelled controls and a layout that survives
 * a narrow viewport.
 */

import { expect, test } from '@playwright/test';

const email = 'learner@example.com';
const password = 'demo-password-123';

test.beforeEach(async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'));
});

test('the skip link is the first tab stop and moves focus to main', async ({ page }) => {
  await page.keyboard.press('Tab');
  await expect(page.locator('.skip-link')).toBeFocused();
  await page.keyboard.press('Enter');
  await expect(page.locator('#main-content')).toBeFocused();
});

test('every navigation item is reachable by keyboard', async ({ page }) => {
  const links = page.locator('.app-sidebar .nav-link');
  const count = await links.count();
  expect(count).toBeGreaterThan(5);
  for (let index = 0; index < count; index += 1) {
    await links.nth(index).focus();
    await expect(links.nth(index)).toBeFocused();
  }
});

test('the search field is labelled and opens with the keyboard shortcut', async ({ page }) => {
  await page.keyboard.press('ControlOrMeta+k');
  await expect(page.getByLabel(/search lessons/i)).toBeFocused();
});

test('form controls have associated labels', async ({ page }) => {
  await page.goto('/settings');
  await expect(page.getByLabel('Display name')).toBeVisible();
  await expect(page.getByLabel('Learning goal')).toBeVisible();
});

test('progress bars expose their value to assistive technology', async ({ page }) => {
  await page.goto('/progress');
  const bar = page.getByRole('progressbar').first();
  await expect(bar).toHaveAttribute('aria-valuenow', /\d+/);
  await expect(bar).toHaveAttribute('aria-valuemax', '100');
});

test('the theme can be toggled and persists across a reload', async ({ page }) => {
  const initial = await page.locator('html').getAttribute('data-theme');
  await page.getByRole('button', { name: /switch to .* theme/i }).click();
  const toggled = await page.locator('html').getAttribute('data-theme');
  expect(toggled).not.toBe(initial);

  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', toggled!);
});

test('the layout is usable on a phone-sized viewport', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto('/learn');
  await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  await expect(page.locator('.app-sidebar')).toBeVisible();

  // No horizontal overflow: the document must not be wider than the viewport.
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
  );
  expect(overflow).toBeLessThanOrEqual(2);
});

test('lesson content reflows into one column on a tablet', async ({ page }) => {
  await page.setViewportSize({ width: 820, height: 1100 });
  await page.goto('/learn/python-fundamentals');
  const columns = await page
    .locator('.lesson-layout')
    .evaluate((element) => getComputedStyle(element).gridTemplateColumns.split(' ').length);
  expect(columns).toBe(1);
});

test('headings form a sensible outline on the lesson page', async ({ page }) => {
  await page.goto('/learn/functions');
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1);
  expect(await page.getByRole('heading', { level: 2 }).count()).toBeGreaterThan(1);
});

test('the error state of a failed submission is announced', async ({ page }) => {
  await page.goto('/practice/fundamentals-hello');
  const editor = page.locator('.monaco-editor').first();
  await editor.click();
  await page.keyboard.press('ControlOrMeta+a');
  await page.keyboard.insertText('print("wrong on purpose")');
  await page.getByRole('button', { name: 'Submit', exact: true }).click();

  const live = page.locator('[aria-live="polite"]');
  await expect(live).toBeVisible({ timeout: 45_000 });
});
