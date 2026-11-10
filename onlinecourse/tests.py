from django.test import TestCase
from django.contrib.auth.models import User
from django.urls import reverse

from .models import Choice, Course, Enrollment, Question


class ExamTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='learner', password='password')
        self.course = Course.objects.create(
            name='Test course',
            description='Course description',
            image='',
        )
        self.question = Question.objects.create(
            course=self.course,
            question_text='Select the correct answer',
            grade=2,
        )
        self.correct_choice = Choice.objects.create(
            question=self.question,
            choice_text='Correct',
            is_correct=True,
        )
        self.wrong_choice = Choice.objects.create(
            question=self.question,
            choice_text='Incorrect',
        )
        self.enrollment = Enrollment.objects.create(
            user=self.user,
            course=self.course,
        )
        self.client.force_login(self.user)

    def test_is_get_score_requires_exact_correct_choice_set(self):
        self.assertTrue(self.question.is_get_score([self.correct_choice.id]))
        self.assertFalse(self.question.is_get_score([]))
        self.assertFalse(self.question.is_get_score([self.wrong_choice.id]))
        self.assertFalse(
            self.question.is_get_score(
                [self.correct_choice.id, self.wrong_choice.id]
            )
        )

    def test_course_details_shows_exam_to_enrolled_user(self):
        response = self.client.get(
            reverse('onlinecourse:course_details', args=[self.course.id])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.templates[0].name,
            'onlinecourse/course_details_bootstrap.html',
        )
        self.assertTrue(response.context['is_enrolled'])
        self.assertContains(response, f'name="choice_{self.correct_choice.id}"')

    def test_enrolled_user_can_submit_and_view_exam_result(self):
        response = self.client.post(
            reverse('onlinecourse:submit', args=[self.course.id]),
            {f'choice_{self.correct_choice.id}': str(self.correct_choice.id)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['score'], 2)
        self.assertEqual(response.context['total_score'], 2)
        self.assertEqual(response.context['grade'], 100)
        self.assertTrue(response.context['passed'])
        self.assertContains(response, 'Congratulations, learner!')

    def test_wrong_answer_is_failed_and_choices_are_highlighted(self):
        response = self.client.post(
            reverse('onlinecourse:submit', args=[self.course.id]),
            {f'choice_{self.wrong_choice.id}': str(self.wrong_choice.id)},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['grade'], 0)
        self.assertFalse(response.context['passed'])
        self.assertContains(response, 'Failed')
        self.assertContains(response, 'list-group-item-danger">Incorrect')
        self.assertContains(response, 'list-group-item-warning">Correct')

    def test_result_is_scoped_to_the_enrolled_user(self):
        submission = self.enrollment.submission_set.create()
        other_user = User.objects.create_user(
            username='another-learner',
            password='password',
        )
        self.client.force_login(other_user)

        response = self.client.get(
            reverse(
                'onlinecourse:show_exam_result',
                args=[self.course.id, submission.id],
            )
        )

        self.assertEqual(response.status_code, 404)
