from rest_framework import serializers
from .models import *
class QuizSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'total_questions', 'created_at', 'updated_at']
        read_only_fields = ['id', 'total_questions', 'created_at', 'updated_at']

class OptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Option
        fields = ['id', 'option_text', 'is_correct']


class QuestionSerializer(serializers.ModelSerializer):
    options = OptionSerializer(many=True)

    class Meta:
        model = Question
        fields = ['id', 'question_text', 'options']


class ItemSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, write_only=True, required=False)
    questions_detail = QuestionSerializer(many=True, read_only=True, source='questions')
    category = serializers.IntegerField(write_only=True)

    class Meta:
        model = Item
        fields = ['id', 'title', 'subtitle', 'button_label', 'access_mode', 'item_type', 'questions', 'questions_detail', 'category']

    def create(self, validated_data):
        category_id = validated_data.pop('category')
        questions_data = validated_data.pop('questions', [])
        category = Category.objects.get(id=category_id)

        item = Item.objects.create(category=category, **validated_data)

        for question_data in questions_data:
            # If Question has nested options, handle them here.
            question = Question.objects.create(**question_data)
            item.questions.add(question)

        return item



class CategorySerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True, write_only=True, required=False)

    class Meta:
        model = Category
        fields = ['id', 'title','access_mode', 'category_type', 'items', 'quiz']

    def create(self, validated_data):
        
        category = Category.objects.create(**validated_data)
        return category
