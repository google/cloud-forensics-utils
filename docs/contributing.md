### Contributing

#### Before you contribute

We love contributions! Read this page (including the small print at the end).

Before we can use your code, you must sign the
[Google Individual Contributor License Agreement](https://developers.google.com/open-source/cla/individual?csw=1)
(CLA), which you can do online. The CLA is necessary mainly because you own the
copyright to your changes, even after your contribution becomes part of our
codebase, so we need your permission to use and distribute your code. We also
need to be sure of various other things—for instance that you'll tell us if you
know that your code infringes on other people's patents. You don't have to sign
the CLA until after you've submitted your code for review and a member has
approved it, but you must do it before we can put your code into our codebase.
Before you start working on a larger contribution, you should get in touch with
us first through the issue tracker with your idea so that we can help out and
possibly guide you. Coordinating up front makes it much easier to avoid
frustration later on.

We use the github
[fork and pull review process](https://help.github.com/articles/using-pull-requests)
to review all contributions. First, fork the cloud-forensics-utils repository by
following the [github instructions](https://help.github.com/articles/fork-a-repo).
Then check out your personal fork:

    $ git clone https://github.com/<username>/cloud-forensics-utils.git

Add an upstream remote so you can easily keep up to date with the main
repository:

    $ git remote add upstream https://github.com/google/cloud-forensics-utils.git

To update your local repo from the main:

    $ git pull upstream master

Please follow the Style Guide when making your changes, and also make sure to
use the project's
[pylintrc](https://github.com/google/cloud-forensics-utils/blob/master/.pylintrc)
and
[yapf config file](https://github.com/google/cloud-forensics-utils/blob/master/.style.yapf).
Once you're ready for review make sure the tests pass:

    $ nosetests -v tests

Commit your changes to your personal fork and then use the GitHub Web UI to
create and send the pull request. We'll review and merge the change.

#### Code review

All submissions, including submissions by project members, require review. To
keep the code base maintainable and readable all code is developed using a
similar coding style. It ensures:

The code should be easy to maintain and understand. As a developer you'll
sometimes find yourself thinking hmm, what is the code supposed to do here. It
is important that you should be able to come back to code 5 months later and
still quickly understand what it supposed to be doing. Also for other people
that want to contribute it is necessary that they need to be able to quickly
understand the code. Be that said, quick-and-dirty solutions might work in the
short term, but we'll ban them from the code base to gain better long term
quality. With the code review process we ensure that at least two eyes looked
over the code in hopes of finding potential bugs or errors (before they become
bugs and errors). This also improves the overall code quality and makes sure
that every developer knows to (largely) expect the same coding style.

#### Style guide

We primarily follow the
[Log2Timeline Python Style Guide](https://github.com/log2timeline/l2tdocs/blob/master/process/Style-guide.md).

#### The small print

Contributions made by corporations are covered by a different agreement than the
one above, the Software Grant and Corporate Contributor License Agreement.
