
## Make a local branch

Make sure you're within the `RecApp` directory and use the command

```
git checkout master
```

to make sure you're branching from the current development branch. Now run

```
git checkout -b my-branch-name
```

Your branch should be named something suitable for the changes you will be making. We also usually include our GitHub username in the branch name as `username/suitable-branch-name`.

## Make your changes in the branch

Create the necessary changes to fix your bug/add your feature. When writing commit messages follow these rules:

1. Separate subject from body with a blank line — This makes your commit easier to read.
2. Limit the subject line to 50 characters — Subject lines should be short and to the point.
3. Capitalize the subject line — This is stylistic, but makes things clearer.
4. Do not end the subject line with a period — Trailing punctuation is an unnecessary waste of space.
5. Use the imperative case in the subject line i.e. As an instruction — This makes it clearer what your patch does.
6. Wrap the body at 72 characters — This makes reading your messages easier for people with small displays.
7. Use the body to explain what and why, rather than how — When looking through the git history at changes it may not be obvious why a change was implemented, making code impossible to maintain.
8. Use Conventional Commits recommendations https://www.conventionalcommits.org/en/v1.0.0/.

## Push your changes to the remote

It is also good practice to rebase your changes before pushing (so that your commits are on top of the target branch), to do this run

```
git rebase origin/master
```

while your branch is checked out. This may require you to force-push your branch, to do this add the `-f` switch to the git push command.
