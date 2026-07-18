# Import Flask-WTF base form and field/validator utilities for input validation.
from flask_wtf import FlaskForm
from wtforms import StringField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, NumberRange, Length, ValidationError, Email, Optional

# Form schema for user registration and creation flows.
class UserForm(FlaskForm):
    username = StringField('Username', validators=[
        DataRequired(message="Username is required"),
        Length(min=3, max=50, message="Username must be between 3 and 50 characters")
    ])
    email = StringField('Email', validators=[
        DataRequired(message="Email is required"),
        Email(message="Invalid email address"),
        Length(max=255, message="Email must be 255 characters or less")
    ])
    password = StringField('Password', validators=[
        DataRequired(message="Password is required"),
        Length(min=8, message="Password must be at least 8 characters")
    ])
    
    # Enforce allowed username characters for consistent identity keys.
    def validate_username(self, field):
        # Reject usernames with disallowed characters to protect routing and display.
        if not field.data.replace('_', '').isalnum():
            raise ValidationError('Username can only contain letters, numbers, and underscores')

# Form schema for partial user profile updates.
class UserUpdateForm(FlaskForm):
    username = StringField('Username', validators=[
        Optional(),
        Length(min=3, max=50, message="Username must be between 3 and 50 characters")
    ])
    email = StringField('Email', validators=[
        Optional(),
        Email(message="Invalid email address"),
        Length(max=255, message="Email must be 255 characters or less")
    ])
    password = StringField('Password', validators=[
        Optional(),
        Length(min=8, message="Password must be at least 8 characters")
    ])

    # Validate optional username changes with the same constraints as registration.
    def validate_username(self, field):
        # Skip validation when no username is provided.
        if field.data and not field.data.replace('_', '').isalnum():
            raise ValidationError('Username can only contain letters, numbers, and underscores')


# Form schema for quest create/update operations.
class QuestForm(FlaskForm):
    title = StringField('Quest Title', validators=[
        DataRequired(message="Quest title is required"),
        Length(min=5, max=100, message="Title must be between 5 and 100 characters")
    ])
    description = TextAreaField('Description', validators=[
        DataRequired(message="Description is required"),
        Length(min=10, max=500, message="Description must be between 10 and 500 characters")
    ])
    reward = IntegerField('Reward Points', validators=[
        DataRequired(message="Reward points are required"),
        NumberRange(min=10, max=10000, message="Reward must be between 10 and 10,000 points")
    ])
    total_required = IntegerField('Times to Complete', validators=[
        DataRequired(message="Total required is needed"),
        NumberRange(min=1, max=100, message="Must be between 1 and 100")
    ])


# Form schema for landmark creation and editing with validation rules.
class LandmarkForm(FlaskForm):
    name = StringField('Landmark Name', validators=[
        DataRequired(message="Landmark name is required"),
        Length(min=3, max=100, message="Name must be between 3 and 100 characters")
    ])
    icon = StringField('Icon Emoji', validators=[
        DataRequired(message="Icon is required"),
        Length(max=10, message="Icon must be 10 characters or less")
    ])
    story = TextAreaField('Story', validators=[
        DataRequired(message="Story is required"),
        Length(min=20, max=1000, message="Story must be between 20 and 1000 characters")
    ])
    question = StringField('Quiz Question', validators=[
        DataRequired(message="Question is required"),
        Length(min=10, max=200, message="Question must be between 10 and 200 characters")
    ])
    correct_answer = IntegerField('Correct Answer Index', validators=[
        DataRequired(message="Correct answer index is required"),
        NumberRange(min=0, max=3, message="Answer index must be between 0 and 3")
    ])
    x_coord = IntegerField('X Coordinate', validators=[
        DataRequired(message="X coordinate is required"),
        NumberRange(min=0, max=800, message="X must be between 0 and 800")
    ])
    y_coord = IntegerField('Y Coordinate', validators=[
        DataRequired(message="Y coordinate is required"),
        NumberRange(min=0, max=550, message="Y must be between 0 and 550")
    ])
