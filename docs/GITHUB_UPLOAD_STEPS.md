# GitHub Upload Steps

1. Create a new GitHub repository.
2. Name it something like `airline-turnaround-analysis`.
3. Upload the contents of this folder.
4. Do not upload `data/raw` or `data/processed`.
5. Go to the repo's **Settings** tab.
6. Click **Pages**.
7. Under **Build and deployment**, choose **Deploy from a branch**.
8. Choose the `main` branch and `/root`.
9. Click **Save**.

After GitHub Pages finishes, the dashboard will load from `index.html`.

If GitHub says a file is too large, check that `data/processed` was not uploaded.
