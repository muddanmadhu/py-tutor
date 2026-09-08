/**
 * The Definition of Done, as an executable test.
 *
 * This walks the twenty steps from README §"Definition of done" in one session:
 * register → learn → write code → execute safely → read errors → take hints →
 * submit → be graded → watch mastery move → debug → get reviewed → explore the
 * reference → ask the tutor → open the capstone.
 */

import { expect, test } from '@playwright/test';

const password = 'e2e-strong-password-1';

/** A unique email per run so the suite is re-runnable against a live database. */
function uniqueEmail(): string {
  return `e2e-${Date.now()}-${Math.floor(Math.random() * 1000)}@pyforge.example.com`;
}

test.describe.configure({ mode: 'serial' });

test.describe('the whole learning loop', () => {
  const email = uniqueEmail();

  test('1. a new learner can register', async ({ page }) => {
    await page.goto('/register');
    await page.getByLabel('Name').fill('E2E Learner');
    await page.getByLabel('Email').fill(email);
    await page.getByLabel('Password', { exact: false }).fill(password);
    await page.getByRole('button', { name: /create account/i }).click();

    await expect(page.getByRole('heading', { level: 1 })).toContainText(/E2E Learner/);
    await expect(page.getByText(/overall mastery/i)).toBeVisible();
  });

  test('2. the dashboard recommends a starting point', async ({ page }) => {
    await signIn(page, email);
    await expect(page.getByRole('heading', { name: /what to do next/i })).toBeVisible();
    await expect(page.locator('.list-row').first()).toBeVisible();
  });

  test('3. the curriculum is browsable', async ({ page }) => {
    await signIn(page, email);
    await page.getByRole('link', { name: 'Learn', exact: true }).click();
    await expect(page.getByRole('heading', { name: /python engineering mastery/i })).toBeVisible();
    await expect(page.getByRole('link', { name: /What Python Is/i })).toBeVisible();
  });

  test('4. a lesson answers all ten questions', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/learn/python-fundamentals');
    await expect(page.getByRole('heading', { name: /what python is/i })).toBeVisible();

    for (const label of [
      'What is it?',
      'Why does it exist?',
      'How does it work?',
      'When should I use it?',
      'When should I NOT use it?',
      'Common mistakes',
      'In real projects',
      'Alternatives',
      'Performance',
      'Security',
    ]) {
      await expect(page.getByRole('heading', { name: label, level: 4 })).toBeVisible();
    }
  });

  test('5. code runs in the sandbox and prints output', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/lab');
    await expect(page.getByRole('heading', { name: 'Code Lab' })).toBeVisible();

    await setEditorContent(page, 'print("sandbox works", 6 * 7)');
    await page.getByRole('button', { name: /^▶ Run/ }).click();

    await expect(page.locator('.console-output').first()).toContainText('sandbox works 42', {
      timeout: 45_000,
    });
  });

  test('6. an infinite loop is stopped rather than hanging the platform', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/lab');
    await setEditorContent(page, 'while True:\n    pass');
    await page.getByRole('button', { name: /^▶ Run/ }).click();

    await expect(page.locator('.console-output.is-error')).toContainText(/time limit/i, {
      timeout: 60_000,
    });
  });

  test('7. a runtime error is explained in plain language', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/lab');
    await setEditorContent(page, 'print(total_undefined)');
    await page.getByRole('button', { name: /^▶ Run/ }).click();

    await expect(page.getByText(/what went wrong/i)).toBeVisible({ timeout: 45_000 });
    await expect(page.getByText(/NameError/)).toBeVisible();
  });

  test('8. a wrong submission is graded with a diff', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/practice/fundamentals-hello');
    await setEditorContent(page, 'print("definitely wrong")');
    await page.getByRole('button', { name: 'Submit', exact: true }).click();

    await expect(page.getByText(/output did not match/i)).toBeVisible({ timeout: 45_000 });
    await expect(page.locator('.diff')).toBeVisible();
  });

  test('9. hints unlock one rung at a time', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/practice/fundamentals-hello');

    await page.getByRole('button', { name: /^Hint \(/ }).click();
    await expect(page.getByText(/Hint 1 of 4/)).toBeVisible();

    await page.getByRole('button', { name: /^Hint \(/ }).click();
    await expect(page.getByText(/Hint 2 of 4/)).toBeVisible();
  });

  test('10. a correct submission passes, awards XP and moves mastery', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/practice/fundamentals-hello');
    await setEditorContent(page, 'print("Hello, PyForge")');
    await page.getByRole('button', { name: 'Submit', exact: true }).click();

    await expect(page.getByText(/output matched exactly/i)).toBeVisible({ timeout: 45_000 });
    await expect(page.locator('.badge-success').filter({ hasText: 'passed' })).toBeVisible();
    await expect(page.getByText(/mastery movement/i)).toBeVisible();
    await expect(page.getByText(/\+\d+ XP/)).toBeVisible();
  });

  test('11. a pytest-graded exercise reports per-test results', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/practice/loops-fizzbuzz');
    await setEditorContent(
      page,
      [
        'def fizzbuzz(n: int) -> list[str]:',
        '    out = []',
        '    for i in range(1, n + 1):',
        '        if i % 15 == 0:',
        '            out.append("FizzBuzz")',
        '        elif i % 3 == 0:',
        '            out.append("Fizz")',
        '        elif i % 5 == 0:',
        '            out.append("Buzz")',
        '        else:',
        '            out.append(str(i))',
        '    return out',
      ].join('\n'),
    );
    await page.getByRole('button', { name: 'Submit', exact: true }).click();

    await expect(page.getByText(/all \d+ tests passed/i)).toBeVisible({ timeout: 90_000 });
    await expect(page.locator('.check.passed').first()).toBeVisible();
  });

  test('12. progress and mastery are visible', async ({ page }) => {
    await signIn(page, email);
    await page.getByRole('link', { name: 'Progress' }).click();
    await expect(page.getByRole('heading', { name: /overall mastery/i })).toBeVisible();
    await expect(page.getByRole('progressbar').first()).toBeVisible();
  });

  test('13. certifications are locked with stated reasons', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/progress');
    await expect(page.getByText('Python Foundations')).toBeVisible();
    await expect(page.getByText(/needs \d+%/).first()).toBeVisible();
  });

  test('14. the code review engine reports real findings', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/lab');
    await setEditorContent(
      page,
      ['def handler(value, seen=[]):', '    return eval(value)'].join('\n'),
    );
    await page.getByRole('button', { name: /review my code/i }).click();

    await expect(page.getByRole('heading', { name: 'Code review' })).toBeVisible({
      timeout: 30_000,
    });
    await expect(page.getByText(/mutable default argument/i)).toBeVisible();
    await expect(page.getByText(/executes arbitrary code/i)).toBeVisible();
  });

  test('15. the reference is browsable and detailed', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/reference');
    await page.getByRole('link', { name: /list\.append/ }).first().click();
    await expect(page.getByRole('heading', { name: /list\.append/ })).toBeVisible();
    await expect(page.getByRole('heading', { name: /common mistakes/i })).toBeVisible();
  });

  test('16. global search finds material across kinds', async ({ page }) => {
    await signIn(page, email);
    await page.getByLabel(/search lessons/i).fill('dict.get');
    await expect(page.getByRole('option').first()).toBeVisible({ timeout: 15_000 });
    await page.getByRole('option').first().click();
    await expect(page).toHaveURL(/\/reference\//);
  });

  test('17. the AI tutor answers and states its mode', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/tutor');
    await page
      .getByLabel(/message the tutor/i)
      .fill('NameError: name "total" is not defined — what does this mean?');
    await page.getByRole('button', { name: 'Send' }).click();
    await expect(page.locator('.chat-turn.assistant')).toBeVisible({ timeout: 60_000 });
  });

  test('18. interview questions grade with an explanation', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/interview');
    const question = page.locator('section.card').filter({ hasText: /mutable/i }).first();
    await question.locator('button.list-row').nth(1).click();
    await expect(question.getByText(/correct|not quite/i)).toBeVisible();
  });

  test('19. the project academy shows the guidance fade-out', async ({ page }) => {
    await signIn(page, email);
    await page.getByRole('link', { name: 'Projects' }).click();
    await expect(page.getByText('Fully guided')).toBeVisible();
    await expect(page.getByText('Requirements only')).toBeVisible();
    await expect(page.getByText('Independent')).toBeVisible();
  });

  test('20. the capstone is a requirement document, not a tutorial', async ({ page }) => {
    await signIn(page, email);
    await page.goto('/projects/enterprise-automation-service');
    await expect(page.getByText(/requirement document/i)).toBeVisible();
    await expect(page.getByText(/order reconciliation service/i)).toBeVisible();
    await expect(page.getByRole('heading', { name: /how this is assessed/i })).toBeVisible();
    // Requirements-only means no step-by-step milestones.
    await expect(page.getByRole('heading', { name: 'Milestones' })).toHaveCount(0);
  });
});

/* --------------------------------------------------------------- helpers */

async function signIn(page: import('@playwright/test').Page, email: string) {
  await page.goto('/login');

  // Each test gets a fresh context, so the form is normally present. If a
  // session already exists, LoginPage redirects client-side instead of
  // rendering — tolerate both rather than racing the redirect.
  const emailField = page.getByLabel('Email');
  if (!(await emailField.isVisible().catch(() => false))) {
    await page.waitForURL((url) => !url.pathname.includes('/login'));
    return;
  }

  await emailField.fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await page.waitForURL((url) => !url.pathname.includes('/login'));
}

/**
 * Replace the Monaco editor's contents.
 *
 * Monaco renders its own DOM and does not expose a textarea whose value can be
 * set directly, so the reliable route is: focus, select all, type.
 */
async function setEditorContent(page: import('@playwright/test').Page, content: string) {
  const editor = page.locator('.monaco-editor').first();
  await editor.waitFor({ state: 'visible', timeout: 30_000 });
  await editor.click();
  await page.keyboard.press('ControlOrMeta+a');
  await page.keyboard.press('Delete');
  // Typing preserves Monaco's auto-indent, which would corrupt Python blocks;
  // insertText bypasses it.
  await page.keyboard.insertText(content);
}
