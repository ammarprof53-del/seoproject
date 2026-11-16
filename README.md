# Programmatic SEO starter

Generate one static software comparison page per CSV row. The generator uses Python 3.9+ and its standard library. There are no package installs, API keys or paid generation calls. The sample dataset contains six original trial plans.

## Run locally

From the extracted project folder, run:

```bash
python3 generator.py
python3 -m http.server 8000 --bind 127.0.0.1 --directory dist
```

Open [the local site](http://127.0.0.1:8000/). A comparison lives at a clean path such as `/notion-vs-confluence-for-team-knowledge-base/`. The underlying file is `dist/notion-vs-confluence-for-team-knowledge-base/index.html`. Stop the server with Ctrl+C.

To verify a production build locally, pass the actual public URL including the project path:

```bash
python3 generator.py --base-url https://YOUR-USERNAME.github.io/seoproject/
```

This adds canonical links and `dist/sitemap.xml`. During deployment, the workflow supplies this URL automatically. Each successful build replaces `dist/`, so keep hand-written files outside it.

## Publish with GitHub Pages

1. [Create a new public repository](https://github.com/new) named `seoproject`. Leave the initialization options unchecked.
2. From the extracted project folder, run the commands below. Replace `YOUR-USERNAME` with your GitHub username and authenticate when Git prompts you.

   ```bash
   git init -b main
   git add dataset.csv template.html generator.py README.md .gitignore .github/workflows/pages.yml
   git commit -m "Create comparison site"
   git remote add origin https://github.com/YOUR-USERNAME/seoproject.git
   git push -u origin main
   ```

3. Open **Settings → Pages** in the repository. Set **Build and deployment → Source** to **GitHub Actions**. Then go to **Actions → Publish comparison site → Run workflow** and choose `main` for the first deployment.
4. After the deploy job succeeds, open the URL reported by the workflow. For a repository named `seoproject`, the default URL is `https://YOUR-USERNAME.github.io/seoproject/`. Check the homepage, one comparison and `sitemap.xml`.
5. Push subsequent edits to `main` to regenerate and deploy automatically. You can also run the workflow manually from the same Actions screen.

GitHub Free supports Pages for public repositories and standard GitHub-hosted runners are free for this use. GitHub Pages restricts sites used to run an online business or primarily to facilitate commercial transactions or provide commercial SaaS. Confirm that your intended use fits before deploying. [Pages limits](https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits) · [Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions) · [Pages workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)

## Add comparisons

- Keep the required CSV headers `Target Tool`, `Competitor`, and `Use Case`. Use UTF-8 and quote cells containing commas.
- Fill in the optional `Workflow Scenario` and `Evaluation Checklist` columns for each published row. Separate checklist items with `|`. The sample scenarios are trial instructions. Add firsthand results or verified details where readers need a decision.
- The `{{AIGeneratedContent}}` slot receives HTML assembled by Python from the row. The three required columns work on their own and use a generic trial checklist. The two optional fields give each page practical detail.
- The slug uses all three required fields. Editing any of them can change the URL. Duplicate slugs fail the build, so resolve collisions before pushing. Slugs currently normalize to ASCII and require each of the three fields to yield at least one ASCII letter or digit.
- Add rows with distinct reader needs. Generating near-identical pages for keyword variants can fall under Google's scaled content abuse policy. [Google Search spam policies](https://developers.google.com/search/docs/essentials/spam-policies#scaled-content)
- The templates use the requested Tailwind Play CDN. Styling requires network access in the browser. Tailwind recommends compiling CSS for a production site. [Tailwind Play CDN](https://tailwindcss.com/docs/installation/play-cdn)
